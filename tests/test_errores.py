"""
NuevaMente — Pruebas del catálogo de errores (src/errores.py).

Ejecutar:  pytest tests/test_errores.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.errores import (  # noqa: E402
    ETAPA_POR_CODIGO,
    MENSAJE_POR_DEFECTO,
    CodigoError,
    ErrorTemaNoCubierto,
)


def test_todo_codigo_tiene_mensaje_y_etapa():
    """Un código nuevo sin mensaje o sin etapa rompe como_respuesta() en ejecución."""
    for codigo in CodigoError:
        assert codigo in MENSAJE_POR_DEFECTO, f"{codigo.value} no tiene mensaje"
        assert codigo in ETAPA_POR_CODIGO, f"{codigo.value} no tiene etapa"


def test_tema_no_cubierto_tras_la_aclaracion():
    """Loop HITL del Investigador: sin coincidencia tras la aclaración, status error."""
    d = ErrorTemaNoCubierto("0 chunks sobre 0.83 para 'Product Owner'").como_respuesta()
    d = d.model_dump(mode="json")
    assert d["status"] == "error"
    assert d["error"]["codigo"] == "TEMA_NO_CUBIERTO"
    assert d["error"]["etapa"] == "recuperacion"
    assert "0.83" not in d["error"]["mensaje_usuario"]
