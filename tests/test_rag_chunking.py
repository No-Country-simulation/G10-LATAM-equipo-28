"""
NuevaMente — Pruebas del chunking con página.

Usan chunks chicos (200/40) para que un documento corto ya cruce páginas.

Ejecutar:  pytest tests/test_rag_chunking.py -v
"""

from __future__ import annotations

import dataclasses
import sys
from itertools import pairwise
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.chunking import _unir_paginas, dividir_en_chunks  # noqa: E402
from src.rag.configuracion import ConfigRAG  # noqa: E402
from src.rag.normalizador import normalizar_por_pagina  # noqa: E402

# Mínimo bajo para probar con textos cortos; el de 100 tiene su propia prueba.
# Sin fusión: estas pruebas miran el divisor; la fusión tiene las suyas, al final.
CONFIG = ConfigRAG(chunk_size=200, chunk_overlap=40, chunk_minimo=20, chunk_fusion=0)
# Para la fusión: sin solapamiento, y dos párrafos de 185 que no caben juntos.
CONFIG_SIN_FUSION = ConfigRAG(chunk_size=200, chunk_overlap=0, chunk_minimo=10, chunk_fusion=0)
CONFIG_FUSION = dataclasses.replace(CONFIG_SIN_FUSION, chunk_fusion=60)


def _pagina(palabra: str, veces: int = 50) -> str:
    return " ".join(f"{palabra}{i}" for i in range(veces))


PAGINAS = [_pagina("alfa"), _pagina("beta"), _pagina("gamma")]


def test_cada_chunk_sabe_en_que_pagina_empieza_y_termina():
    chunks = dividir_en_chunks(PAGINAS, "doc1", CONFIG)
    vocabulario = {1: "alfa", 2: "beta", 3: "gamma"}
    for chunk in chunks:
        palabras = chunk.texto.split()
        assert palabras[0].startswith(vocabulario[chunk.pagina])
        assert palabras[-1].startswith(vocabulario[chunk.pagina_fin])
        assert chunk.pagina <= chunk.pagina_fin


def test_paginas_cortas_quedan_juntas_en_un_chunk():
    cortas = [_pagina("alfa", 8), _pagina("beta", 8), _pagina("gamma", 8)]
    chunks = dividir_en_chunks(cortas, "doc1", CONFIG)
    assert len(chunks) == 1
    assert (chunks[0].pagina, chunks[0].pagina_fin) == (1, 3)


def test_una_pagina_larga_se_divide_sola():
    chunks = dividir_en_chunks(PAGINAS, "doc1", CONFIG)
    assert all(c.pagina == c.pagina_fin for c in chunks)
    assert {c.pagina for c in chunks} == {1, 2, 3}


def test_el_inicio_apunta_al_texto_del_chunk():
    chunks = dividir_en_chunks(PAGINAS, "doc1", CONFIG)
    texto, _ = _unir_paginas(normalizar_por_pagina(PAGINAS))
    for chunk in chunks:
        assert texto[chunk.inicio : chunk.inicio + len(chunk.texto)] == chunk.texto


def test_una_pagina_vacia_no_corre_la_numeracion():
    chunks = dividir_en_chunks([_pagina("alfa"), "", _pagina("gamma")], "doc1", CONFIG)
    assert {c.pagina for c in chunks if c.texto.startswith("gamma")} == {3}


def test_las_paginas_vacias_no_dejan_saltos_de_mas():
    [chunk] = dividir_en_chunks(["Portada de la guía", "", "  ", "Contenido real del capítulo"], "d", CONFIG)
    assert chunk.texto == "Portada de la guía\n\nContenido real del capítulo"
    assert (chunk.pagina, chunk.pagina_fin) == (1, 4)


def test_ids_consecutivos_y_orden():
    chunks = dividir_en_chunks(PAGINAS, "doc1", CONFIG)
    assert [c.chunk_id for c in chunks] == [f"c{i:04d}" for i in range(1, len(chunks) + 1)]
    assert [c.orden for c in chunks] == list(range(len(chunks)))
    assert all(c.document_id == "doc1" for c in chunks)


def test_respeta_el_tamano_y_se_solapan_dentro_de_la_pagina():
    chunks = dividir_en_chunks(PAGINAS, "doc1", CONFIG)
    assert all(len(c.texto) <= CONFIG.chunk_size for c in chunks)
    seguidos = [(a, b) for a, b in zip(chunks, chunks[1:], strict=False) if a.pagina == b.pagina]
    assert seguidos
    assert all(b.inicio < a.inicio + len(a.texto) for a, b in seguidos)


def test_texto_suelto_se_divide_sin_pagina():
    chunks = dividir_en_chunks("\n\n".join(PAGINAS), "doc1", CONFIG)
    assert chunks and all(c.pagina is None and c.pagina_fin is None for c in chunks)


def test_normaliza_antes_de_dividir():
    chunks = dividir_en_chunks(["- 4 - 5 Resp onsabilidades Integrales del Scrum Maste r ¥ con el equipo"], "d", CONFIG)
    texto = " ".join(c.texto for c in chunks)
    assert "Responsabilidades" in texto and "Master" in texto and "¥" not in texto


def test_sin_normalizar_respeta_el_texto():
    original = "Resp onsabilidades del Scrum Maste r en el equipo"
    chunks = dividir_en_chunks([original], "d", CONFIG, normalizar_texto=False)
    assert chunks[0].texto == original


def test_descarta_los_chunks_minimos():
    assert len("Hola") < CONFIG.chunk_minimo
    assert dividir_en_chunks(["Hola"], "d", CONFIG) == []
    assert dividir_en_chunks(["", "  "], "d", CONFIG) == []


def test_sin_fusion_la_portada_sola_no_se_indexa():
    # Hallazgo de T2-06: la portada de la guía (28 caracteres) salía primera
    # en consultas ajenas. Sin fusión, CHUNK_MINIMO=100 la descarta.
    config = ConfigRAG(chunk_fusion=0)
    assert config.chunk_minimo == 100
    chunks = dividir_en_chunks(["GUÍA SCRUM MASTER\n2025\nv.1.0", _pagina("alfa", 300)], "doc1", config)
    assert chunks and all(c.pagina == 2 for c in chunks)
    assert all(len(c.texto) >= 100 for c in chunks)


def test_con_la_configuracion_por_defecto_la_portada_se_une_al_primer_chunk():
    config = ConfigRAG()
    chunks = dividir_en_chunks(["GUÍA SCRUM MASTER\n2025\nv.1.0", _pagina("alfa", 300)], "doc1", config)
    assert chunks[0].texto.startswith("GUÍA SCRUM MASTER")
    assert (chunks[0].pagina, chunks[0].pagina_fin) == (1, 2)
    assert sum("GUÍA SCRUM MASTER" in c.texto for c in chunks) == 1
    assert all(len(c.texto) >= config.chunk_minimo for c in chunks)


def test_la_tabla_de_contenido_no_llega_a_los_chunks():
    paginas = [
        "GUÍA SCRUM MASTER\n2025\nv.1.0",
        "1 Tableof Contents\n2 Objetivos de la Guía - 3 -\n3 El Rol - 3 -\n4 Los eventos - 4 -",
        "2 Objetivos de la Guía\n" + _pagina("alfa", 40),
    ]
    texto = "\n".join(c.texto for c in dividir_en_chunks(paginas, "doc1", CONFIG))
    assert "Tableof" not in texto and "- 3 -" not in texto
    assert "2 Objetivos de la Guía" in texto and "alfa39" in texto


def test_saltos_de_linea_de_windows_no_llegan_a_los_chunks():
    chunks = dividir_en_chunks(["Primera línea del Scrum Master\r\nSegunda línea del equipo Scrum"], "d", CONFIG)
    assert chunks and all("\r" not in c.texto for c in chunks)


@pytest.mark.parametrize("tamano,solapamiento", [(1000, 150), (500, 50)])
def test_con_la_configuracion_del_plan(tamano, solapamiento):
    config = ConfigRAG(chunk_size=tamano, chunk_overlap=solapamiento)
    paginas = [_pagina(p, 300) for p in ("alfa", "beta", "gamma", "delta")]
    chunks = dividir_en_chunks(paginas, "doc1", config)
    assert all(len(c.texto) <= tamano + config.chunk_fusion for c in chunks)
    assert {c.pagina for c in chunks} == {1, 2, 3, 4}


# =============================================================================
# Fusión de los chunks cortos (CHUNK_FUSION)
# =============================================================================


def _parrafo(palabra: str) -> str:
    return _pagina(palabra, 28)  # 185 caracteres


def _dividir(fuente: str | list[str], config: ConfigRAG):
    paginas = [fuente] if isinstance(fuente, str) else fuente
    return dividir_en_chunks(paginas, "d", config, normalizar_texto=False)


def test_un_fragmento_corto_se_une_al_anterior():
    pagina = _parrafo("alfa") + "\n\nfin del capítulo con cierre"
    assert [len(c.texto) for c in _dividir(pagina, CONFIG_SIN_FUSION)] == [185, 27]
    assert [c.texto for c in _dividir(pagina, CONFIG_FUSION)] == [pagina]


def test_un_titulo_suelto_se_une_a_su_seccion():
    pagina = _parrafo("alfa") + "\n\n12 Qué evitar: roles\n\n" + _parrafo("beta")
    primero, segundo = _dividir(pagina, CONFIG_FUSION)
    assert primero.texto == _parrafo("alfa")
    assert segundo.texto == "12 Qué evitar: roles\n\n" + _parrafo("beta")


def test_si_el_corto_es_el_primero_se_une_al_siguiente():
    pagina = "Introducción breve\n\n" + _parrafo("alfa")
    assert [c.texto for c in _dividir(pagina, CONFIG_FUSION)] == [pagina]


def test_si_no_cabe_con_el_vecino_queda_solo():
    config = dataclasses.replace(CONFIG_SIN_FUSION, chunk_fusion=20)  # tope: 200 + 20
    pagina = "a" * 200 + "\n\ncola de diecinueve."
    assert [c.texto for c in _dividir(pagina, config)] == ["a" * 200, "cola de diecinueve."]


def test_cada_chunk_se_ubica_despues_del_anterior():
    # El divisor corta «b» * 200 en 199 + 1: esa «b» suelta también aparece dentro
    # del chunk anterior, pero se tiene que ubicar donde la cortó el divisor.
    config = dataclasses.replace(CONFIG_SIN_FUSION, chunk_minimo=1)
    pagina = "a" * 200 + "\n\ncola de diecinueve.\n\n" + "b" * 200
    chunks = _dividir(pagina, config)
    assert chunks[-1].texto == "b" and chunks[-1].inicio == len(pagina) - 1
    for anterior, chunk in pairwise(chunks):
        assert chunk.inicio >= anterior.inicio + len(anterior.texto) - config.chunk_overlap


def test_la_union_no_repite_el_solapamiento():
    config = ConfigRAG(chunk_size=200, chunk_overlap=40, chunk_minimo=10, chunk_fusion=100)
    pagina = _pagina("alfa", 60)
    sin_fusion = _dividir(pagina, dataclasses.replace(config, chunk_fusion=0))
    con_fusion = _dividir(pagina, config)
    assert len(con_fusion) < len(sin_fusion)
    for chunk in con_fusion:
        palabras = chunk.texto.split()
        assert len(palabras) == len(set(palabras))
        assert pagina[chunk.inicio : chunk.inicio + len(chunk.texto)] == chunk.texto


def test_la_union_conserva_las_paginas_y_los_ids():
    chunks = _dividir([_parrafo("alfa"), "cola corta de la página dos", _parrafo("beta")], CONFIG_FUSION)
    assert [(c.pagina, c.pagina_fin) for c in chunks] == [(1, 2), (3, 3)]
    assert [c.chunk_id for c in chunks] == ["c0001", "c0002"]
