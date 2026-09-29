"""
NuevaMente — Pruebas de la configuración del RAG.

No leen el .env real: cada prueba pasa su propio `entorno`.

Ejecutar:  pytest tests/test_rag_configuracion.py -v
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.configuracion import (  # noqa: E402
    RAIZ_REPO,
    ConfigRAG,
    cargar_config,
)
from src.rag.errores import RAG_CONFIGURACION, ErrorConfiguracionRAG  # noqa: E402

TOKEN = "hf_tokenDePrueba123456"


def test_valores_por_defecto_del_plan():
    cfg = cargar_config(entorno={})
    assert cfg.modelo_embeddings == "intfloat/multilingual-e5-base"
    assert cfg.proveedor_embeddings == "hf-inference"
    assert cfg.dimension_embeddings == 768
    assert (cfg.chunk_size, cfg.chunk_overlap, cfg.chunk_minimo) == (1000, 150, 100)
    assert cfg.top_k == 5
    assert cfg.umbral_retrieval == 0.82  # provisional desde T2-06; el plan decía 0.78
    assert cfg.tamano_lote == 32
    assert cfg.chroma_path == (RAIZ_REPO / "chroma_db").resolve()
    assert cfg.hf_token is None and not cfg.tiene_token
    assert cfg.url_embeddings is None


def test_lee_una_url_propia_para_los_embeddings():
    cfg = cargar_config(entorno={"EMBEDDINGS_URL": "https://mi-endpoint.ejemplo/embed"})
    assert cfg.url_embeddings == "https://mi-endpoint.ejemplo/embed"
    assert "url=https://mi-endpoint.ejemplo/embed" in cfg.resumen_seguro()


def test_raiz_del_repo_es_la_carpeta_de_src():
    assert (RAIZ_REPO / "src" / "rag" / "configuracion.py").is_file()


def test_lee_las_variables_del_entorno():
    cfg = cargar_config(
        entorno={
            "HF_TOKEN": TOKEN,
            "EMBEDDINGS_MODELO": "intfloat/multilingual-e5-large",
            "EMBEDDINGS_PROVEEDOR": "otro-proveedor",
            "EMBEDDINGS_DIMENSION": "1024",
            "EMBEDDINGS_LOTE": "16",
            "EMBEDDINGS_TIMEOUT": "12.5",
            "EMBEDDINGS_REINTENTOS": "0",
            "CHUNK_SIZE": "800",
            "CHUNK_OVERLAP": "100",
            "CHUNK_MINIMO": "50",
            "RETRIEVAL_TOP_K": "8",
            "UMBRAL_RETRIEVAL": "0.82",
        }
    )
    assert cfg.hf_token == TOKEN
    assert cfg.modelo_embeddings == "intfloat/multilingual-e5-large"
    assert cfg.proveedor_embeddings == "otro-proveedor"
    assert cfg.dimension_embeddings == 1024
    assert cfg.tamano_lote == 16
    assert cfg.timeout_segundos == 12.5
    assert cfg.reintentos == 0
    assert (cfg.chunk_size, cfg.chunk_overlap, cfg.chunk_minimo, cfg.top_k) == (800, 100, 50, 8)
    assert cfg.umbral_retrieval == 0.82


def test_acepta_el_nombre_de_langchain_para_el_token():
    cfg = cargar_config(entorno={"HUGGINGFACEHUB_API_TOKEN": TOKEN})
    assert cfg.hf_token == TOKEN


def test_hf_token_gana_sobre_el_nombre_de_langchain():
    cfg = cargar_config(entorno={"HF_TOKEN": TOKEN, "HUGGINGFACEHUB_API_TOKEN": "hf_otro123456"})
    assert cfg.hf_token == TOKEN


def test_token_vacio_cuenta_como_ausente():
    assert cargar_config(entorno={"HF_TOKEN": "   "}).hf_token is None


def test_con_entorno_explicito_no_mira_el_entorno_real(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", TOKEN)
    assert cargar_config(entorno={}).hf_token is None


def test_el_token_no_aparece_en_repr_ni_en_el_resumen():
    cfg = cargar_config(entorno={"HF_TOKEN": TOKEN})
    assert TOKEN not in repr(cfg)
    assert TOKEN not in cfg.resumen_seguro()
    assert "token=presente" in cfg.resumen_seguro()


def test_resumen_avisa_si_falta_el_token():
    assert "token=AUSENTE" in cargar_config(entorno={}).resumen_seguro()


def test_acepta_coma_decimal():
    assert cargar_config(entorno={"UMBRAL_RETRIEVAL": "0,8"}).umbral_retrieval == 0.8


def test_chroma_path_relativo_cuenta_desde_la_raiz_del_repo():
    cfg = cargar_config(entorno={"CHROMA_PATH": "./datos/indice"})
    assert cfg.chroma_path == (RAIZ_REPO / "datos" / "indice").resolve()


def test_chroma_path_absoluto_se_respeta(tmp_path):
    cfg = cargar_config(entorno={"CHROMA_PATH": str(tmp_path / "indice")})
    assert cfg.chroma_path == (tmp_path / "indice").resolve()


def test_la_ruta_tambien_se_resuelve_al_construir_directo():
    assert ConfigRAG(chroma_path="relativa").chroma_path == (RAIZ_REPO / "relativa").resolve()


def test_es_inmutable_y_replace_valida_de_nuevo():
    cfg = cargar_config(entorno={})
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.tamano_lote = 8  # type: ignore[misc]
    assert dataclasses.replace(cfg, tamano_lote=8).tamano_lote == 8
    with pytest.raises(ErrorConfiguracionRAG):
        dataclasses.replace(cfg, tamano_lote=0)


@pytest.mark.parametrize(
    "entorno,fragmento",
    [
        ({"CHUNK_SIZE": "500", "CHUNK_OVERLAP": "500"}, "CHUNK_OVERLAP"),
        ({"CHUNK_OVERLAP": "-1"}, "CHUNK_OVERLAP"),
        ({"UMBRAL_RETRIEVAL": "1.5"}, "UMBRAL_RETRIEVAL"),
        ({"UMBRAL_RETRIEVAL": "0"}, "UMBRAL_RETRIEVAL"),
        ({"EMBEDDINGS_LOTE": "0"}, "EMBEDDINGS_LOTE"),
        ({"EMBEDDINGS_LOTE": "treinta"}, "EMBEDDINGS_LOTE"),
        ({"EMBEDDINGS_TIMEOUT": "0"}, "EMBEDDINGS_TIMEOUT"),
        ({"EMBEDDINGS_REINTENTOS": "-2"}, "EMBEDDINGS_REINTENTOS"),
        ({"RETRIEVAL_TOP_K": "0"}, "RETRIEVAL_TOP_K"),
        ({"UMBRAL_RETRIEVAL": "alto"}, "UMBRAL_RETRIEVAL"),
        ({"EMBEDDINGS_URL": "ftp://servidor/embed"}, "EMBEDDINGS_URL"),
        ({"CHUNK_SIZE": "500", "CHUNK_MINIMO": "500"}, "CHUNK_MINIMO"),
        ({"CHUNK_MINIMO": "-1"}, "CHUNK_MINIMO"),
    ],
)
def test_valores_invalidos_dan_un_error_claro(entorno, fragmento):
    with pytest.raises(ErrorConfiguracionRAG) as info:
        cargar_config(entorno=entorno)
    assert info.value.codigo == RAG_CONFIGURACION
    assert fragmento in info.value.detalle
    # El mensaje para el usuario final no nombra variables internas.
    assert fragmento not in info.value.mensaje


def test_junta_todos_los_problemas_en_un_solo_error():
    with pytest.raises(ErrorConfiguracionRAG) as info:
        cargar_config(entorno={"EMBEDDINGS_LOTE": "0", "RETRIEVAL_TOP_K": "0"})
    assert "EMBEDDINGS_LOTE" in info.value.detalle
    assert "RETRIEVAL_TOP_K" in info.value.detalle
