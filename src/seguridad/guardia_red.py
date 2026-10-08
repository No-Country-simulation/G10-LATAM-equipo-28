"""Política de destinos de red para integraciones conocidas de NuevaMente.

Esta validación en proceso reduce destinos accidentales y SSRF por URL; no
reemplaza reglas de salida de red, DNS pinning ni controles de OCI.
"""

from __future__ import annotations

import ipaddress
import os
import re
import socket
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit, urlunsplit


class ErrorGuardiaRed(ValueError):
    """Destino de red rechazado por política."""


DOMINIOS_PERMITIDOS = frozenset({
    "api.groq.com",
    "generativelanguage.googleapis.com",
    "api.deepseek.com",
    "api.moonshot.cn",
    "api.anthropic.com",
    "huggingface.co",
    "router.huggingface.co",
    "openaipublic.blob.core.windows.net",
})

ENDPOINTS_PROVEEDOR = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com",
    "deepseek": "https://api.deepseek.com/v1",
    "kimi": "https://api.moonshot.cn/v1",
    "anthropic": "https://api.anthropic.com",
}

_REGION_OCI = re.compile(r"^objectstorage\.[a-z0-9-]+\.oraclecloud\.com$")
_NOMBRE_HOST = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*$")
_ALLOWLIST_ENV = "NUEVAMENTE_RED_ALLOWLIST"


def _host_ascii(host: str) -> str:
    try:
        return ipaddress.ip_address(host).compressed.lower()
    except ValueError:
        pass
    try:
        host = host.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise ErrorGuardiaRed("El destino tiene un nombre de host inválido.") from None
    if not _NOMBRE_HOST.fullmatch(host):
        raise ErrorGuardiaRed("El destino tiene un nombre de host inválido.")
    return host


def _leer_allowlist(extra: Iterable[str] | None) -> frozenset[str]:
    valores = set(DOMINIOS_PERMITIDOS)
    valores.update(host.lower().strip().rstrip(".") for host in (extra or ()) if host.strip())
    configurados = os.getenv(_ALLOWLIST_ENV, "")
    if configurados.strip():
        valores.update(host.strip().rstrip(".").lower() for host in configurados.split(",") if host.strip())
    normalizados = set()
    for host in valores:
        if "*" in host or "/" in host or ":" in host:
            raise ErrorGuardiaRed(f"La allowlist contiene una entrada no exacta: {host!r}.")
        normalizados.add(_host_ascii(host))
    return frozenset(normalizados)


def _es_loopback_ollama(host: str, puerto: int, permitir_ollama_local: bool) -> bool:
    if not permitir_ollama_local or puerto != 11434:
        return False
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _es_host_permitido(host: str, allowlist: frozenset[str]) -> bool:
    return host in allowlist or bool(_REGION_OCI.fullmatch(host))


def _validar_ips_publicas(host: str, puerto: int, resolver: Callable[..., Iterable] | None) -> None:
    try:
        ip_directa = ipaddress.ip_address(host)
        ips = [ip_directa]
    except ValueError:
        if resolver is None:
            resolver = socket.getaddrinfo
        try:
            registros = resolver(host, puerto, type=socket.SOCK_STREAM)
        except OSError:
            raise ErrorGuardiaRed("No se pudo resolver el destino autorizado.") from None
        ips = []
        for registro in registros:
            direccion = registro[4][0]
            try:
                ips.append(ipaddress.ip_address(direccion))
            except ValueError:
                raise ErrorGuardiaRed("La resolución devolvió una dirección inválida.") from None
    if not ips:
        raise ErrorGuardiaRed("El destino no resolvió direcciones de red.")
    if any(not ip.is_global for ip in ips):
        raise ErrorGuardiaRed("El destino resuelve a una dirección local o reservada.")


def validar_url_destino(
    url: str,
    *,
    allowlist: Iterable[str] | None = None,
    permitir_ollama_local: bool = False,
    resolver_dns: bool = False,
    resolver: Callable[..., Iterable] | None = None,
) -> str:
    """Valida esquema, host, puerto y opcionalmente todas las IP resueltas.

    Las redirecciones deben volver a pasar por esta función antes de seguirse.
    No se aceptan comodines en la allowlist. Por defecto, la resolución DNS se
    deja al transporte del proveedor; `resolver_dns=True` sirve en integraciones
    HTTP que puedan fijar y reutilizar de forma segura las IP comprobadas.
    """
    if not isinstance(url, str) or not url.strip() or len(url) > 2_048:
        raise ErrorGuardiaRed("La URL de destino está vacía o supera el límite permitido.")
    try:
        partes = urlsplit(url.strip())
        host_original = partes.hostname
        puerto = partes.port
    except ValueError:
        raise ErrorGuardiaRed("La URL de destino está malformada.") from None
    if partes.scheme.lower() not in {"http", "https"} or not host_original:
        raise ErrorGuardiaRed("Solo se aceptan destinos HTTP o HTTPS con host.")
    if partes.username is not None or partes.password is not None:
        raise ErrorGuardiaRed("La URL no puede incluir credenciales.")
    host = _host_ascii(host_original)
    puerto = puerto or (443 if partes.scheme.lower() == "https" else 80)
    local = _es_loopback_ollama(host, puerto, permitir_ollama_local)
    if local:
        if partes.scheme.lower() != "http":
            raise ErrorGuardiaRed("Ollama local debe usar HTTP solo en loopback y puerto 11434.")
    else:
        if partes.scheme.lower() != "https" or puerto != 443:
            raise ErrorGuardiaRed("Los destinos externos deben usar HTTPS en el puerto estándar.")
        if not _es_host_permitido(host, _leer_allowlist(allowlist)):
            raise ErrorGuardiaRed("El host de destino no está en la allowlist de NuevaMente.")
        if resolver_dns:
            _validar_ips_publicas(host, puerto, resolver)
    ruta = partes.path or "/"
    host_url = f"[{host}]" if ":" in host else host
    return urlunsplit((partes.scheme.lower(), f"{host_url}:{puerto}" if puerto not in (80, 443) else host_url,
                       ruta, partes.query, ""))


def validar_endpoint_proveedor(proveedor: str, url: str | None = None) -> str:
    """Valida el endpoint efectivo de un proveedor antes de construir su cliente."""
    nombre = proveedor.lower().strip()
    if nombre == "ollama":
        if not url:
            raise ErrorGuardiaRed("Falta la URL local de Ollama.")
        return validar_url_destino(url, permitir_ollama_local=True)
    esperado = ENDPOINTS_PROVEEDOR.get(nombre)
    destino = url or esperado
    if not destino:
        raise ErrorGuardiaRed("El proveedor no tiene un endpoint aprobado.")
    validado = validar_url_destino(destino)
    if esperado and validado != validar_url_destino(esperado):
        raise ErrorGuardiaRed("El endpoint no coincide con el proveedor configurado.")
    return validado


def validar_redireccion(url_destino: str, **opciones) -> str:
    """Revalida un Location HTTP con las mismas reglas de destino."""
    return validar_url_destino(url_destino, **opciones)
