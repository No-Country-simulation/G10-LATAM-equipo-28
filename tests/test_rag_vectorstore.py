"""
NuevaMente — Pruebas del índice en Chroma, una colección por document_id (D-07).

Chroma corre de verdad, en una carpeta temporal; los vectores salen de
embeddings falsos, sin red.

Ejecutar:  pytest tests/test_rag_vectorstore.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag_falsos import EmbeddingsFalsos  # noqa: E402

from src.rag import errores as e  # noqa: E402
from src.rag.chunking import dividir_en_chunks  # noqa: E402
from src.rag.configuracion import ConfigRAG  # noqa: E402
from src.rag.errores import ErrorRAG  # noqa: E402
from src.rag.vectorstore import AlmacenChroma, firma_de  # noqa: E402

PAGINAS = [
    "El Scrum Master facilita los eventos y elimina impedimentos del equipo.",
    "El Product Owner ordena el Product Backlog y maximiza el valor.",
    "Los Developers construyen el incremento durante el Sprint.",
]


@pytest.fixture()
def config(tmp_path) -> ConfigRAG:
    return ConfigRAG(chroma_path=tmp_path / "chroma", chunk_size=80, chunk_overlap=10, chunk_minimo=10)


@pytest.fixture()
def almacen(config) -> AlmacenChroma:
    return AlmacenChroma(config)


@pytest.fixture()
def indexado(almacen, config):
    chunks = dividir_en_chunks(PAGINAS, "doc1", config)
    vectores = EmbeddingsFalsos().embed_documents([c.texto for c in chunks])
    almacen.guardar("doc1", chunks, vectores)
    return chunks, vectores


def test_guarda_y_cuenta(almacen, indexado):
    chunks, _ = indexado
    assert almacen.cantidad("doc1") == len(chunks) == 3
    assert almacen.esta_indexado("doc1")


@pytest.mark.filterwarnings("ignore:legacy embedding function config:DeprecationWarning")
def test_una_coleccion_por_documento_con_distancia_coseno(almacen, indexado):
    coleccion = almacen.cliente.get_collection("doc_doc1", embedding_function=None)
    assert coleccion.configuration["hnsw"]["space"] == "cosine"
    assert coleccion.metadata["firma"] == firma_de(almacen.config)
    assert coleccion.metadata["document_id"] == "doc1"


def test_consultar_ordena_por_similitud_y_el_puntaje_es_el_coseno(almacen, indexado):
    chunks, vectores = indexado
    consulta = EmbeddingsFalsos().embed_query("Scrum Master impedimentos")
    resultados = almacen.consultar("doc1", consulta, top_k=3)
    assert [r.chunk_id for r in resultados][0] == "c0001"
    puntajes = [r.score for r in resultados]
    assert puntajes == sorted(puntajes, reverse=True)
    esperado = float(np.dot(vectores[0], consulta))
    assert resultados[0].score == pytest.approx(esperado, abs=1e-5)
    assert resultados[0].metadatos["pagina"] == 1


def test_top_k_no_pasa_de_la_cantidad_de_chunks(almacen, indexado):
    consulta = EmbeddingsFalsos().embed_query("Sprint")
    assert len(almacen.consultar("doc1", consulta, top_k=50)) == 3
    assert almacen.consultar("doc1", consulta, top_k=0) == []


def test_vectores_de_chunks_respeta_el_orden_pedido(almacen, indexado):
    _, vectores = indexado
    obtenidos = almacen.vectores_de_chunks("doc1", ["c0003", "c0001"])
    assert np.allclose(obtenidos[0], vectores[2], atol=1e-6)
    assert np.allclose(obtenidos[1], vectores[0], atol=1e-6)
    assert almacen.vectores_de_chunks("doc1", []) == []


def test_vectores_de_un_chunk_que_no_existe(almacen, indexado):
    with pytest.raises(ErrorRAG) as info:
        almacen.vectores_de_chunks("doc1", ["c0001", "c0099"])
    assert info.value.codigo == e.RAG_CHUNK_NO_ENCONTRADO
    assert "c0099" in info.value.detalle


def test_el_indice_persiste_entre_instancias(config, indexado):
    assert AlmacenChroma(config).esta_indexado("doc1")


def test_otra_configuracion_invalida_el_indice(config, indexado):
    otra = ConfigRAG(chroma_path=config.chroma_path, chunk_size=120, chunk_overlap=10)
    almacen = AlmacenChroma(otra)
    assert almacen.cantidad("doc1") == 3
    assert not almacen.esta_indexado("doc1")


def test_guardar_de_nuevo_rehace_la_coleccion(almacen, config, indexado):
    chunks = dividir_en_chunks(PAGINAS[:1], "doc1", config)
    almacen.guardar("doc1", chunks, EmbeddingsFalsos().embed_documents([c.texto for c in chunks]))
    assert almacen.cantidad("doc1") == 1


def test_documento_sin_indexar(almacen):
    assert not almacen.esta_indexado("otro")
    assert almacen.cantidad("otro") == 0
    with pytest.raises(ErrorRAG) as info:
        almacen.consultar("otro", [0.1] * 768, top_k=5)
    assert info.value.codigo == e.RAG_DOCUMENTO_NO_INDEXADO


def test_borrar(almacen, indexado):
    assert almacen.borrar("doc1") is True
    assert not almacen.esta_indexado("doc1")
    assert almacen.borrar("doc1") is False


@pytest.mark.parametrize("document_id", ["", "con espacio", "../fuera", "a" * 61])
def test_document_id_invalido(almacen, document_id):
    with pytest.raises(ErrorRAG):
        almacen.esta_indexado(document_id)


def test_guardar_valida_lo_que_recibe(almacen, config):
    chunks = dividir_en_chunks(PAGINAS, "doc1", config)
    vectores = EmbeddingsFalsos().embed_documents([c.texto for c in chunks])
    with pytest.raises(ErrorRAG):
        almacen.guardar("doc1", [], [])
    with pytest.raises(ErrorRAG):
        almacen.guardar("doc1", chunks, vectores[:-1])
    with pytest.raises(ErrorRAG):
        almacen.guardar("doc1", chunks, [v[:10] for v in vectores])
    with pytest.raises(ErrorRAG):
        almacen.guardar("doc2", chunks, vectores)  # chunks de otro documento


def test_chunks_sin_pagina_se_guardan_sin_ese_metadato(almacen, config):
    chunks = dividir_en_chunks(" ".join(PAGINAS), "doc3", config)
    almacen.guardar("doc3", chunks, EmbeddingsFalsos().embed_documents([c.texto for c in chunks]))
    resultado = almacen.consultar("doc3", EmbeddingsFalsos().embed_query("Product Owner"), top_k=1)[0]
    assert "pagina" not in resultado.metadatos
