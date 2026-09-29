"""
NuevaMente — Pruebas de la indexación (calcular_document_id, indexar_documento).

Lo importante: el mismo documento da el mismo id venga del disco o del MCP, y
un documento ya indexado no vuelve a gastar embeddings.

Ejecutar:  pytest tests/test_rag_indexacion.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag_falsos import EmbeddingsFalsos, crear_pdf  # noqa: E402

from src.rag import errores as e  # noqa: E402
from src.rag.configuracion import ConfigRAG  # noqa: E402
from src.rag.embeddings import EmbeddingsE5  # noqa: E402
from src.rag.errores import ErrorRAG  # noqa: E402
from src.rag.extraccion import extraer_paginas, texto_como_mcp  # noqa: E402
from src.rag.indexacion import calcular_document_id, indexar_archivo, indexar_documento  # noqa: E402
from src.rag.vectorstore import AlmacenChroma  # noqa: E402

PAGINAS = [
    "El Scrum Master facilita los eventos y elimina impedimentos del equipo. " * 4,
    "El Product Owner ordena el Product Backlog y maximiza el valor del producto. " * 4,
    "Los Developers construyen un incremento utilizable durante cada Sprint. " * 4,
]


@pytest.fixture()
def almacen(tmp_path) -> AlmacenChroma:
    return AlmacenChroma(ConfigRAG(chroma_path=tmp_path / "chroma", chunk_size=200, chunk_overlap=20))


# =============================================================================
# document_id
# =============================================================================


def test_document_id_son_16_caracteres_hexadecimales():
    document_id = calcular_document_id(PAGINAS)
    assert len(document_id) == 16
    int(document_id, 16)


def test_mismo_id_desde_las_paginas_o_desde_el_texto_del_mcp():
    assert calcular_document_id(PAGINAS) == calcular_document_id(texto_como_mcp(PAGINAS))
    assert calcular_document_id(PAGINAS) == calcular_document_id("\n\n".join(PAGINAS) + "  \n")


def test_otro_texto_otro_id():
    assert calcular_document_id(PAGINAS) != calcular_document_id(PAGINAS[:2])


@pytest.mark.parametrize("vacio", ["", "   \n", [], ["", "  "]])
def test_documento_vacio(vacio):
    with pytest.raises(ErrorRAG) as info:
        calcular_document_id(vacio)
    assert info.value.codigo == e.RAG_DOCUMENTO_VACIO


# =============================================================================
# indexar_documento
# =============================================================================


def test_indexa_y_devuelve_la_cantidad_de_chunks(almacen):
    embeddings = EmbeddingsFalsos()
    document_id = calcular_document_id(PAGINAS)
    cantidad = indexar_documento(document_id, PAGINAS, embeddings=embeddings, almacen=almacen)
    assert cantidad == almacen.cantidad(document_id) > 0
    assert embeddings.textos_documentos == cantidad


def test_lo_ya_indexado_no_gasta_embeddings(almacen):
    embeddings = EmbeddingsFalsos()
    document_id = calcular_document_id(PAGINAS)
    primera = indexar_documento(document_id, PAGINAS, embeddings=embeddings, almacen=almacen)
    llamadas = embeddings.llamadas_documentos
    segunda = indexar_documento(document_id, PAGINAS, embeddings=embeddings, almacen=almacen)
    assert segunda == primera
    assert embeddings.llamadas_documentos == llamadas


def test_forzar_reindexa(almacen):
    embeddings = EmbeddingsFalsos()
    document_id = calcular_document_id(PAGINAS)
    indexar_documento(document_id, PAGINAS, embeddings=embeddings, almacen=almacen)
    indexar_documento(document_id, PAGINAS, embeddings=embeddings, almacen=almacen, forzar=True)
    assert embeddings.llamadas_documentos == 2


def test_si_cambia_el_chunking_se_reindexa_solo(almacen, tmp_path):
    document_id = calcular_document_id(PAGINAS)
    indexar_documento(document_id, PAGINAS, embeddings=EmbeddingsFalsos(), almacen=almacen)
    otra = AlmacenChroma(ConfigRAG(chroma_path=almacen.config.chroma_path, chunk_size=120, chunk_overlap=20))
    embeddings = EmbeddingsFalsos()
    indexar_documento(document_id, PAGINAS, embeddings=embeddings, almacen=otra)
    assert embeddings.llamadas_documentos == 1
    assert otra.esta_indexado(document_id)


def test_texto_del_mcp_se_indexa_sin_pagina(almacen):
    texto = texto_como_mcp(PAGINAS)
    document_id = calcular_document_id(texto)
    indexar_documento(document_id, texto, embeddings=EmbeddingsFalsos(), almacen=almacen)
    resultado = almacen.consultar(document_id, EmbeddingsFalsos().embed_query("Product Owner"), top_k=1)[0]
    assert "pagina" not in resultado.metadatos


def test_documento_sin_chunks_utiles(almacen):
    with pytest.raises(ErrorRAG) as info:
        indexar_documento("corto", ["Hola"], embeddings=EmbeddingsFalsos(), almacen=almacen)
    assert info.value.codigo == e.RAG_DOCUMENTO_VACIO


def test_embeddings_de_otro_modelo_no_se_mezclan(almacen):
    otro_modelo = EmbeddingsE5(ConfigRAG(hf_token="hf_x123456789", modelo_embeddings="otro/modelo"), cliente=object())
    with pytest.raises(ErrorRAG) as info:
        indexar_documento("doc", PAGINAS, embeddings=otro_modelo, almacen=almacen)
    assert info.value.codigo == e.RAG_INDICE


# =============================================================================
# indexar_archivo
# =============================================================================


def test_indexar_un_pdf_conserva_la_pagina(almacen, tmp_path):
    pdf = crear_pdf(tmp_path / "guia.pdf", [
        "El Scrum Master facilita los eventos de Scrum y elimina impedimentos.",
        "El Product Owner ordena el Product Backlog para maximizar el valor.",
    ])
    document_id, cantidad = indexar_archivo(pdf, embeddings=EmbeddingsFalsos(), almacen=almacen)
    assert document_id == calcular_document_id(extraer_paginas(pdf))
    assert cantidad >= 1
    resultado = almacen.consultar(document_id, EmbeddingsFalsos().embed_query("Product Backlog"), top_k=1)[0]
    assert resultado.metadatos["pagina"] in (1, 2)
