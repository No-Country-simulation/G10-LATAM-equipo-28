import socket
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from src.seguridad.guardia_red import (
    ErrorGuardiaRed,
    validar_endpoint_proveedor,
    validar_redireccion,
    validar_url_destino,
)


def test_permite_proveedor_https_conocido():
    assert validar_endpoint_proveedor("groq") == "https://api.groq.com/openai/v1"


@pytest.mark.parametrize("url", [
    "https://api.groq.com.evil.example/v1",
    "http://api.groq.com/v1",
    "https://usuario:clave@api.groq.com/v1",
    "https://127.0.0.1/v1",
    "https://169.254.169.254/latest/meta-data",
    "http://10.0.0.4:8080/admin",
    "file:///etc/passwd",
    "https://api.groq.com:8443/v1",
    "https://[::1]/",
])
def test_rechaza_destinos_malformados_o_sensibles(url):
    with pytest.raises(ErrorGuardiaRed):
        validar_url_destino(url)


def test_ollama_solo_puede_usar_loopback_en_puerto_local():
    assert validar_endpoint_proveedor("ollama", "http://127.0.0.1:11434") == "http://127.0.0.1:11434/"
    with pytest.raises(ErrorGuardiaRed):
        validar_endpoint_proveedor("ollama", "http://192.168.1.8:11434")
    with pytest.raises(ErrorGuardiaRed):
        validar_endpoint_proveedor("ollama", "http://127.0.0.1:8080")


def test_permite_endpoint_de_object_storage_por_region():
    assert validar_url_destino("https://objectstorage.us-ashburn-1.oraclecloud.com/n/ns/b/bucket/o/file")


def test_allowlist_rechaza_comodines_y_acepta_host_extra_exacto(monkeypatch):
    monkeypatch.setenv("NUEVAMENTE_RED_ALLOWLIST", "*.example.com")
    with pytest.raises(ErrorGuardiaRed):
        validar_url_destino("https://api.groq.com")
    monkeypatch.setenv("NUEVAMENTE_RED_ALLOWLIST", "api.example.com")
    assert validar_url_destino("https://api.example.com") == "https://api.example.com/"


def test_resolucion_dns_rechaza_cualquier_ip_no_global():
    def resolver(host, port, type):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.1.2.3", port))]

    with pytest.raises(ErrorGuardiaRed, match="local o reservada"):
        validar_url_destino("https://api.groq.com", resolver_dns=True, resolver=resolver)


def test_redireccion_vuelve_a_aplicar_la_allowlist():
    assert validar_redireccion("https://api.groq.com/v1") == "https://api.groq.com/v1"
    with pytest.raises(ErrorGuardiaRed):
        validar_redireccion("http://127.0.0.1/admin")


def test_factory_ollama_rechaza_base_url_interna_antes_de_construir_cliente(monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    try:
        import llm_provider
        monkeypatch.setattr(
            llm_provider, "settings",
            replace(llm_provider.settings, ollama_base_url="http://169.254.169.254:11434"),
        )
        with pytest.raises(ValueError, match="HTTPS|allowlist"):
            llm_provider._build_chat("ollama", "nomic-embed-text", 0.0)
    finally:
        sys.path.remove(str(Path(__file__).resolve().parents[1] / "src"))


def test_cliente_groq_conserva_el_endpoint_aprobado(monkeypatch):
    ruta_src = str(Path(__file__).resolve().parents[1] / "src")
    sys.path.insert(0, ruta_src)
    try:
        import seguridad.llm_client as cliente
        monkeypatch.setattr(cliente, "GROQ_BASE_URL", "https://api.groq.com.evil.example/openai/v1")
        with pytest.raises(ValueError, match="allowlist"):
            cliente._build_chat_model("openai/gpt-oss-120b", cliente.RateLimiter(), 1, 0.2, 10)
    finally:
        sys.path.remove(ruta_src)
