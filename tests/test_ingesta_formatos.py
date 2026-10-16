"""Criterio de salida de T4-07: los 3 tipos de entrada (PDF, MD, TXT) indexan.

Integra extracción + chunking + embeddings + Chroma con embeddings sin red y un
índice temporal, igual que el resto de pruebas del RAG. No usa el modelo e5 real
ni la API de Hugging Face.

Ejecutar:   pytest tests/test_ingesta_formatos.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.configuracion import ConfigRAG  # noqa: E402
from src.rag.indexacion import indexar_archivo  # noqa: E402
from src.rag.recuperacion import recuperar  # noqa: E402
from src.rag.vectorstore import AlmacenChroma  # noqa: E402
from tests.rag_falsos import EmbeddingsFalsos, crear_pdf  # noqa: E402

TEXTO = (
    "El Scrum Master facilita el proceso y elimina impedimentos. "
    "El Product Owner prioriza el backlog del producto. " * 4
)


def _almacen(tmp_path: Path) -> AlmacenChroma:
    return AlmacenChroma(
        ConfigRAG(chroma_path=tmp_path / "chroma", chunk_size=200, chunk_overlap=20, chunk_fusion=0)
    )


@pytest.mark.parametrize("formato", ["md", "txt", "pdf"])
def test_los_tres_formatos_indexan_y_se_recuperan(tmp_path, formato):
    if formato == "pdf":
        ruta = crear_pdf(tmp_path / "guia.pdf", [TEXTO])
    else:
        ruta = tmp_path / f"guia.{formato}"
        ruta.write_text(TEXTO, encoding="utf-8")

    embeddings = EmbeddingsFalsos()
    almacen = _almacen(tmp_path)

    document_id, cantidad = indexar_archivo(ruta, embeddings=embeddings, almacen=almacen)

    assert document_id
    assert cantidad >= 1
    recuperados = recuperar(
        document_id, "Scrum Master", umbral=-1.0, embeddings=embeddings, almacen=almacen
    )
    assert recuperados, f"{formato} no devolvió chunks"
