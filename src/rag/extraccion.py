"""
NuevaMente — Extracción de texto por página.

Hace lo mismo que `_extraer_texto()` del servidor MCP
(src/servidor_objeStorageOracle.py), pero devuelve una cadena por página en
vez de unirlas. Unidas con "\\n\\n" y sin espacios en los extremos, dan el mismo
`texto_extraido` que devuelve `descargar_documento()`. Por eso el mismo
archivo produce el mismo `document_id`, venga del disco o de OCI.

Formatos: PDF (una cadena por página), Markdown y texto (una sola cadena,
UTF-8 y, si falla, Latin-1, como el MCP).
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path

from . import errores as e
from .errores import ErrorRAG

SEPARADOR_PAGINAS = "\n\n"
EXTENSIONES_PDF = frozenset({".pdf"})
EXTENSIONES_TEXTO = frozenset({".md", ".markdown", ".txt"})


def extraer_paginas(origen: str | Path | bytes, nombre: str | None = None) -> list[str]:
    """
    Devuelve el texto del documento, una cadena por página.

    `origen` es una ruta o el contenido en bytes. Con bytes hace falta `nombre`
    (por ejemplo, el `nombre` que da el MCP) para saber el formato.
    """
    if isinstance(origen, bytes):
        if not nombre:
            raise ValueError("con bytes hace falta el nombre del archivo para saber su formato")
        contenido = origen
    else:
        ruta = Path(origen)
        nombre = nombre or ruta.name
        contenido = ruta.read_bytes()

    extension = Path(nombre).suffix.lower()
    if extension in EXTENSIONES_PDF:
        from pypdf import PdfReader  # import diferido: solo hace falta para PDF

        lector = PdfReader(io.BytesIO(contenido))
        return [pagina.extract_text() or "" for pagina in lector.pages]
    if extension in EXTENSIONES_TEXTO:
        return [_decodificar(contenido)]
    raise ErrorRAG(
        "Ese formato de documento no se puede procesar; usa PDF, Markdown o texto.",
        codigo=e.RAG_FORMATO_NO_SOPORTADO,
        detalle=f"Extensión {extension or '(sin extensión)'!r}.",
    )


def texto_como_mcp(paginas: Sequence[str]) -> str:
    """El `texto_extraido` que devolvería el MCP para estas páginas."""
    return SEPARADOR_PAGINAS.join(paginas).strip()


def _decodificar(contenido: bytes) -> str:
    try:
        return contenido.decode("utf-8")
    except UnicodeDecodeError:
        return contenido.decode("latin-1")
