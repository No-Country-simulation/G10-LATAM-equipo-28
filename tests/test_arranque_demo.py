"""
tests/test_arranque_demo.py

Verifica el contrato de `src/arranque_demo.py`: los respaldos que permiten que
`app.py` arranque cuando faltan `seguridad/auth.py`, `seguridad/cuotas.py` y
`render_documento.py`.

El test más importante es el último: fija los **nombres exactos** que `app.py`
importa en su bloque `except ImportError`. Si alguien borra uno de ahí, `app.py`
vuelve a romperse en silencio y este test lo caza.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import arranque_demo as demo  # noqa: E402


def test_requerir_login_devuelve_un_usuario_con_los_tres_campos():
    usuario = demo.requerir_login()

    assert usuario.user_id == "demo"
    assert usuario.nombre
    assert usuario.email


def test_hay_login_real_es_false_en_modo_demo():
    # app.py lo usa para no ofrecer "Cerrar sesión" (no habría sesión que cerrar).
    assert demo.hay_login_real() is False


def test_consumir_corrida_no_lanza_ni_limita():
    assert demo.consumir_corrida("demo") is None


def test_corridas_restantes_y_limite_no_mienten_con_un_numero():
    # No inventamos cuotas en demo: se muestran etiquetas, no cifras.
    assert demo.corridas_restantes("demo") == "∞"
    assert demo.limite_usuario() == "demo"


def test_error_cuota_conserva_el_mensaje():
    exc = demo.ErrorCuota("sin cupo")

    assert str(exc) == "sin cupo"
    assert exc.mensaje == "sin cupo"


def test_error_cuota_tiene_mensaje_por_defecto():
    assert demo.ErrorCuota().mensaje


@pytest.mark.parametrize("items", [[], [{"id": "i1"}], [{"tipo": "tutorial"}]])
def test_tipo_documento_es_false_para_dejar_el_render_a_app(items):
    # False → app.py usa su propio render (_html_ficha_reporte), que ya existe.
    assert demo.tipo_documento(items) is False


def test_html_documento_devuelve_la_firma_completa_sin_romperse():
    html = demo.html_documento(
        {"titulo": "Guía de prueba"},
        {"formato_generado": "Tutorial"},
        [{"id": "i1"}],
        evaluacion={"anclaje_fuente_score": 0.9},
        almacenamiento={"path": "generados/x.json"},
        status="exito",
    )

    assert isinstance(html, str)
    assert "Guía de prueba" in html


def test_html_documento_tolera_resultado_vacio():
    assert "<h1>" in demo.html_documento({}, {}, [])


def test_el_modulo_expone_todo_lo_que_app_py_importa():
    """Contrato con app.py: si falta un nombre acá, el except de app.py explota."""
    nombres_que_app_importa = {
        # bloque seguridad.auth
        "requerir_login",
        "hay_login_real",
        # bloque seguridad.cuotas
        "ErrorCuota",
        "consumir_corrida",
        "corridas_restantes",
        "limite_usuario",
        # bloque render_documento
        "CSS_DOCUMENTO",
        "tipo_documento",
        "html_documento",
    }

    faltantes = {n for n in nombres_que_app_importa if not hasattr(demo, n)}

    assert not faltantes, f"app.py importaría y no existirían: {sorted(faltantes)}"
