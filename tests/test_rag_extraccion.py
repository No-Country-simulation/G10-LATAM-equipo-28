"""
NuevaMente — Pruebas de la extracción por página.

Los PDF se generan en una carpeta temporal con reportlab.

Ejecutar:  pytest tests/test_rag_extraccion.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag_falsos import crear_pdf  # noqa: E402

from src.rag import errores as e  # noqa: E402
from src.rag.errores import ErrorRAG  # noqa: E402
from src.rag.extraccion import extraer_paginas, texto_como_mcp  # noqa: E402


def test_pdf_devuelve_una_cadena_por_pagina(tmp_path):
    pdf = crear_pdf(tmp_path / "guia.pdf", ["Primera página del Scrum Master", "Segunda: Product Owner", "Tercera"])
    paginas = extraer_paginas(pdf)
    assert len(paginas) == 3
    assert "Scrum Master" in paginas[0]
    assert "Product Owner" in paginas[1]


def test_pagina_sin_texto_queda_vacia_y_no_corre_la_numeracion(tmp_path):
    pdf = crear_pdf(tmp_path / "guia.pdf", ["Uno", "", "Tres"])
    paginas = extraer_paginas(pdf)
    assert len(paginas) == 3
    assert paginas[1].strip() == ""
    assert "Tres" in paginas[2]


def test_markdown_y_texto_son_una_sola_cadena(tmp_path):
    md = tmp_path / "nota.md"
    md.write_text("# Título\n\nEl Scrum Master facilita.", encoding="utf-8")
    txt = tmp_path / "nota.txt"
    txt.write_text("Texto plano con eñe.", encoding="utf-8")
    assert extraer_paginas(md) == ["# Título\n\nEl Scrum Master facilita."]
    assert extraer_paginas(txt) == ["Texto plano con eñe."]


def test_texto_en_latin1_como_el_mcp(tmp_path):
    archivo = tmp_path / "viejo.txt"
    archivo.write_bytes("Configuración".encode("latin-1"))
    assert extraer_paginas(archivo) == ["Configuración"]


def test_bytes_con_nombre(tmp_path):
    pdf = crear_pdf(tmp_path / "guia.pdf", ["Página única"])
    assert extraer_paginas(pdf.read_bytes(), nombre="guia.pdf") == extraer_paginas(pdf)
    assert extraer_paginas(b"hola", nombre="nota.md") == ["hola"]


def test_bytes_sin_nombre_es_un_error_de_programacion():
    with pytest.raises(ValueError):
        extraer_paginas(b"hola")


@pytest.mark.parametrize("nombre", ["informe.docx", "imagen.png", "sin_extension"])
def test_formato_no_soportado(tmp_path, nombre):
    archivo = tmp_path / nombre
    archivo.write_bytes(b"contenido")
    with pytest.raises(ErrorRAG) as info:
        extraer_paginas(archivo)
    assert info.value.codigo == e.RAG_FORMATO_NO_SOPORTADO


def test_texto_como_mcp_une_con_linea_en_blanco_y_recorta():
    assert texto_como_mcp(["  uno", "dos", "tres \n"]) == "uno\n\ndos\n\ntres"
