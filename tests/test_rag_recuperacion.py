"""
NuevaMente — Pruebas de recuperar(), embeder_consultas() y vectores_de_chunks().

Es la interfaz que consumen el Investigador, el Redactor y la fidelidad.

Ejecutar:  pytest tests/test_rag_recuperacion.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag_falsos import EmbeddingsFalsos  # noqa: E402

from src.rag import errores as e  # noqa: E402
from src.rag.configuracion import ConfigRAG  # noqa: E402
from src.rag.errores import ErrorRAG  # noqa: E402
from src.rag.indexacion import calcular_document_id, indexar_documento  # noqa: E402
from src.rag.modelos import ChunkRecuperado  # noqa: E402
from src.rag.recuperacion import embeder_consultas, recuperar, vectores_de_chunks  # noqa: E402
from src.rag.vectorstore import AlmacenChroma  # noqa: E402

PAGINAS = [
    "Responsabilidades del Scrum Master: facilita los eventos, protege al equipo y elimina impedimentos.",
    "El Product Owner es responsable de ordenar el Product Backlog y de maximizar el valor del producto.",
    "Receta de arepas: harina de maíz, agua tibia, sal y un poco de mantequilla.",
]


@pytest.fixture()
def entorno(tmp_path):
    config = ConfigRAG(chroma_path=tmp_path / "chroma", chunk_size=120, chunk_overlap=10, chunk_minimo=20)
    almacen = AlmacenChroma(config)
    embeddings = EmbeddingsFalsos()
    document_id = calcular_document_id(PAGINAS)
    indexar_documento(document_id, PAGINAS, embeddings=embeddings, almacen=almacen)
    return document_id, embeddings, almacen


def test_recupera_el_chunk_que_responde_con_su_pagina(entorno):
    document_id, embeddings, almacen = entorno
    resultado = recuperar(document_id, "responsabilidades del Scrum Master", umbral=0.0,
                          embeddings=embeddings, almacen=almacen)
    assert isinstance(resultado[0], ChunkRecuperado)
    assert "Scrum Master" in resultado[0].texto
    assert resultado[0].pagina == 1
    assert resultado[0].document_id == document_id


def test_vienen_de_mayor_a_menor(entorno):
    document_id, embeddings, almacen = entorno
    resultado = recuperar(document_id, "Product Owner", umbral=-1.0, embeddings=embeddings, almacen=almacen)
    puntajes = [r.score for r in resultado]
    assert puntajes == sorted(puntajes, reverse=True)


def test_el_umbral_filtra(entorno):
    document_id, embeddings, almacen = entorno
    todos = recuperar(document_id, "Scrum Master", umbral=-1.0, embeddings=embeddings, almacen=almacen)
    assert len(todos) == 3
    assert recuperar(document_id, "Scrum Master", umbral=0.99, embeddings=embeddings, almacen=almacen) == []
    corte = todos[0].score
    filtrados = recuperar(document_id, "Scrum Master", umbral=corte, embeddings=embeddings, almacen=almacen)
    assert [r.chunk_id for r in filtrados] == [todos[0].chunk_id]


def test_por_defecto_usa_top_k_y_umbral_de_la_configuracion(entorno):
    document_id, embeddings, almacen = entorno
    assert almacen.config.umbral_retrieval == 0.82 and almacen.config.top_k == 5
    resultado = recuperar(document_id, "arepas", embeddings=embeddings, almacen=almacen)
    assert all(r.score >= 0.82 for r in resultado)


def test_top_k(entorno):
    document_id, embeddings, almacen = entorno
    assert len(recuperar(document_id, "el", top_k=2, umbral=-1.0, embeddings=embeddings, almacen=almacen)) == 2


@pytest.mark.parametrize("consulta", ["", "   "])
def test_consulta_vacia(entorno, consulta):
    document_id, embeddings, almacen = entorno
    with pytest.raises(ErrorRAG) as info:
        recuperar(document_id, consulta, embeddings=embeddings, almacen=almacen)
    assert info.value.codigo == e.RAG_CONSULTA_VACIA


def test_documento_no_indexado(entorno):
    _, embeddings, almacen = entorno
    with pytest.raises(ErrorRAG) as info:
        recuperar("0000000000000000", "Scrum Master", embeddings=embeddings, almacen=almacen)
    assert info.value.codigo == e.RAG_DOCUMENTO_NO_INDEXADO


def test_no_gasta_embeddings_si_el_documento_no_esta_indexado(entorno):
    _, embeddings, almacen = entorno
    antes = embeddings.llamadas_consultas
    with pytest.raises(ErrorRAG):
        recuperar("0000000000000000", "Scrum Master", embeddings=embeddings, almacen=almacen)
    assert embeddings.llamadas_consultas == antes


def test_embeder_consultas_para_la_fidelidad(entorno):
    _, embeddings, _ = entorno
    vectores = embeder_consultas(["El Scrum Master facilita", "Receta de arepas"], embeddings=embeddings)
    assert len(vectores) == 2 and len(vectores[0]) == 768


def test_vectores_de_chunks_son_los_guardados_en_el_mismo_orden(entorno):
    document_id, embeddings, almacen = entorno
    recuperados = recuperar(document_id, "Scrum Master", umbral=-1.0, embeddings=embeddings, almacen=almacen)
    ids = [r.chunk_id for r in recuperados][::-1]
    vectores = vectores_de_chunks(document_id, ids, almacen=almacen)
    textos = {r.chunk_id: r.texto for r in recuperados}
    for chunk_id, vector in zip(ids, vectores, strict=True):
        assert np.allclose(vector, embeddings.vector(textos[chunk_id]), atol=1e-6)
