"""Pruebas del adaptador `RecuperadorRAG` (rag.recuperar -> protocolo `Recuperador`).

Ejecutar:   pytest tests/test_recuperador_rag.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agentes.recuperador_rag import RecuperadorRAG  # noqa: E402
from src.rag.configuracion import ConfigRAG  # noqa: E402
from src.rag.errores import ErrorRAG  # noqa: E402
from src.rag.indexacion import calcular_document_id, indexar_documento  # noqa: E402
from src.rag.vectorstore import AlmacenChroma  # noqa: E402
from tests.rag_falsos import EmbeddingsFalsos  # noqa: E402


def _indice(tmp_path: Path) -> tuple[EmbeddingsFalsos, AlmacenChroma]:
    """Embeddings sin red + Chroma temporal, como el resto de pruebas del RAG."""
    embeddings = EmbeddingsFalsos()
    almacen = AlmacenChroma(
        ConfigRAG(chroma_path=tmp_path / "chroma", chunk_size=200, chunk_overlap=20, chunk_fusion=0)
    )
    return embeddings, almacen


def test_buscar_devuelve_chunks_del_documento_activo(tmp_path):
    embeddings, almacen = _indice(tmp_path)
    texto = "El Scrum Master facilita el proceso y elimina impedimentos. " * 6
    document_id = calcular_document_id(texto)
    indexar_documento(document_id, texto, embeddings=embeddings, almacen=almacen)

    recuperador = RecuperadorRAG(
        document_id=document_id, umbral=-1.0, embeddings=embeddings, almacen=almacen
    )
    chunks = recuperador.buscar("Scrum Master", top_k=3)

    assert chunks
    assert all(chunk.id and chunk.texto for chunk in chunks)


def test_sin_documento_fijado_falla_con_error_del_rag():
    recuperador = RecuperadorRAG()

    assert recuperador.document_id is None
    with pytest.raises(ErrorRAG):
        recuperador.buscar("cualquier cosa")


def test_fijar_documento_ata_el_recuperador(tmp_path):
    embeddings, almacen = _indice(tmp_path)
    texto = "Contenido sobre el Product Owner y el backlog. " * 6
    document_id = calcular_document_id(texto)
    indexar_documento(document_id, texto, embeddings=embeddings, almacen=almacen)

    recuperador = RecuperadorRAG(umbral=-1.0, embeddings=embeddings, almacen=almacen)
    recuperador.fijar_documento(document_id)

    assert recuperador.document_id == document_id
    assert recuperador.buscar("backlog", top_k=2)


def test_umbral_alto_no_devuelve_nada(tmp_path):
    embeddings, almacen = _indice(tmp_path)
    texto = "Una VCN es una red privada y personalizable en la nube. " * 6
    document_id = calcular_document_id(texto)
    indexar_documento(document_id, texto, embeddings=embeddings, almacen=almacen)

    recuperador = RecuperadorRAG(
        document_id=document_id, umbral=0.999, embeddings=embeddings, almacen=almacen
    )

    assert recuperador.buscar("Scrum Master", top_k=3) == []
