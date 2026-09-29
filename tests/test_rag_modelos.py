"""
NuevaMente — Pruebas de los modelos del RAG (Chunk y ChunkRecuperado).

Ejecutar:  pytest tests/test_rag_modelos.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.modelos import Chunk, ChunkRecuperado, formatear_chunk_id  # noqa: E402


def _chunk(**cambios) -> Chunk:
    datos = {
        "chunk_id": "c0001",
        "document_id": "abc123",
        "texto": "El Scrum Master facilita.",
        "orden": 0,
        "inicio": 0,
    }
    return Chunk(**{**datos, **cambios})


@pytest.mark.parametrize("orden,esperado", [(0, "c0001"), (41, "c0042"), (9998, "c9999"), (9999, "c10000")])
def test_formatear_chunk_id(orden, esperado):
    assert formatear_chunk_id(orden) == esperado


@pytest.mark.parametrize("chunk_id", ["1", "c1", "chunk_1", "C0001", ""])
def test_chunk_id_con_formato_invalido(chunk_id):
    with pytest.raises(ValidationError):
        _chunk(chunk_id=chunk_id)


def test_la_pagina_cuenta_desde_1():
    with pytest.raises(ValidationError):
        _chunk(pagina=0)
    assert _chunk(pagina=1, pagina_fin=2).pagina_fin == 2


def test_metadatos_para_chroma_omiten_los_none():
    sin_pagina = _chunk().metadatos()
    assert "pagina" not in sin_pagina and "pagina_fin" not in sin_pagina
    assert None not in sin_pagina.values()
    con_pagina = _chunk(pagina=3, pagina_fin=4).metadatos()
    assert con_pagina["pagina"] == 3 and con_pagina["pagina_fin"] == 4
    assert con_pagina["document_id"] == "abc123"


def test_chunk_es_inmutable_y_no_acepta_campos_de_mas():
    chunk = _chunk()
    with pytest.raises(ValidationError):
        chunk.texto = "otro"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        _chunk(embedding=[0.1])


def test_chunk_recuperado_trae_los_campos_del_plan():
    recuperado = ChunkRecuperado(chunk_id="c0003", texto="...", score=0.83, pagina=5, document_id="abc123")
    assert set(recuperado.model_dump()) == {"chunk_id", "texto", "score", "pagina", "document_id"}
    # Se puede guardar como dict en el estado del grafo y reconstruir.
    assert ChunkRecuperado(**recuperado.model_dump()) == recuperado


def test_chunk_recuperado_sin_pagina_ni_document_id():
    recuperado = ChunkRecuperado(chunk_id="c0001", texto="...", score=0.5)
    assert recuperado.pagina is None and recuperado.document_id is None


@pytest.mark.parametrize("score", [1.5, -1.2])
def test_score_fuera_de_rango(score):
    with pytest.raises(ValidationError):
        ChunkRecuperado(chunk_id="c0001", texto="...", score=score)
