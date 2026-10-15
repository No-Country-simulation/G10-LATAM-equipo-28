"""Smoke test: el grafo se importa y expone la construcción.

Ejecutar:   pytest tests/test_grafo_smoke.py -v

Protege contra la regresión que dejó `main` roto: `grafo.py` importaba módulos
con estilo incompatible (`agentes.supervisor` / `seguridad.rate_limiter`) que no
se podían resolver desde la raíz del repo.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_grafo_se_importa_desde_la_raiz():
    import src.grafo as grafo  # noqa: F401

    assert hasattr(grafo, "construir_grafo")
    assert hasattr(grafo, "nodo_buscador_documentos")
