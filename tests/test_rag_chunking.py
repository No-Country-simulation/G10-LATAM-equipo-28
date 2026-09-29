"""
NuevaMente — Pruebas del chunking con página.

Usan chunks chicos (200/40) para que un documento corto ya cruce páginas.

Ejecutar:  pytest tests/test_rag_chunking.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.chunking import _unir_paginas, dividir_en_chunks  # noqa: E402
from src.rag.configuracion import ConfigRAG  # noqa: E402
from src.rag.normalizador import normalizar_por_pagina  # noqa: E402

# Mínimo bajo para probar con textos cortos; el de 100 tiene su propia prueba.
CONFIG = ConfigRAG(chunk_size=200, chunk_overlap=40, chunk_minimo=20)


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


def test_la_portada_sola_no_se_indexa_con_el_minimo_por_defecto():
    # Hallazgo de T2-06: la portada de la guía (28 caracteres) salía primera
    # en consultas ajenas. Con CHUNK_MINIMO=100 no se indexa.
    config = ConfigRAG()
    assert config.chunk_minimo == 100
    chunks = dividir_en_chunks(["GUÍA SCRUM MASTER\n2025\nv.1.0", _pagina("alfa", 300)], "doc1", config)
    assert chunks and all(c.pagina == 2 for c in chunks)
    assert all(len(c.texto) >= 100 for c in chunks)


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
    assert all(len(c.texto) <= tamano for c in chunks)
    assert {c.pagina for c in chunks} == {1, 2, 3, 4}
