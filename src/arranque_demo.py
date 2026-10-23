"""
arranque_demo.py

Respaldos mínimos para que `app.py` pueda arrancar cuando no están los módulos
que hoy solo existen en la máquina de Franklin:

- `seguridad/auth.py`      → login de Google (`st.login`)
- `seguridad/cuotas.py`    → cuotas de corridas por día
- `render_documento.py`    → CSS y render HTML del documento generado

`app.py` intenta importar los módulos reales y, si no están, cae a estos. El día
que los reales existan, se usan ellos y este archivo queda inerte.

Qué NO es esto: no reemplaza funcionalidad de producto. Es el "modo demo" para
poder levantar la app. El login y las cuotas quedan **fuera del MVP** (decisión
del 16/10); el render cae al que ya trae `app.py` (`_html_ficha_reporte`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

AVISO_MODO_DEMO = "Modo demo: sin login ni cuotas (los módulos no están)."


# --------------------------------------------------------------------------
# seguridad/auth  →  login de Google
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class UsuarioDemo:
    """Usuario fijo del modo demo. Imita lo que `app.py` espera del real.

    `user_id` es el valor que `app.py` usa para aislar documentos en OCI y en
    Chroma; en demo es constante a propósito (no hay sesión real).
    """

    user_id: str = "demo"
    nombre: str = "Modo demo"
    email: str = "demo@nuevamente.local"


def requerir_login() -> UsuarioDemo:
    """Devuelve el usuario de demo en vez de cortar la página pidiendo login."""
    return UsuarioDemo()


def hay_login_real() -> bool:
    """`False` en demo: `app.py` lo usa para no ofrecer 'Cerrar sesión'."""
    return False


# --------------------------------------------------------------------------
# seguridad/cuotas  →  cuotas de corridas por día
# --------------------------------------------------------------------------


class ErrorCuota(Exception):
    """Cuota agotada. En modo demo nunca se lanza; existe por contrato."""

    def __init__(self, mensaje: str = "Cuota agotada.") -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


def consumir_corrida(user_id: str) -> None:
    """No-op: en demo no se limita el uso."""
    return None


def corridas_restantes(user_id: str) -> str:
    """Sin límite en demo (se muestra tal cual en la barra lateral)."""
    return "∞"


def limite_usuario() -> str:
    """Etiqueta del límite en demo (evita mostrar un número inventado)."""
    return "demo"


# --------------------------------------------------------------------------
# render_documento  →  CSS y render HTML del documento
# --------------------------------------------------------------------------

# `app.py` lo inyecta en un <style>; vacío = sin estilo extra (la app ya trae
# el suyo para la interfaz).
CSS_DOCUMENTO = ""


def tipo_documento(items: list[dict[str, Any]]) -> bool:
    """`False` → `app.py` usa su propio render (`_html_ficha_reporte`).

    Esa es la gracia del respaldo: en vez de reimplementar el HTML del
    documento, dejamos que `app.py` renderice con lo que ya tiene.
    """
    return False


def html_documento(
    resultado: dict[str, Any],
    metadatos: dict[str, Any],
    items_dict: list[dict[str, Any]],
    evaluacion: dict[str, Any] | None = None,
    almacenamiento: dict[str, Any] | None = None,
    status: str = "exito",
) -> str:
    """Existe por contrato de firma; no se llama si `tipo_documento` es `False`."""
    titulo = (resultado or {}).get("titulo", "Documento")
    return f"<h1>{titulo}</h1>"
