"""
NuevaMente — Indexación: texto -> normalizador -> chunks -> embeddings -> Chroma.

Es lo que llama el nodo Ingesta del grafo:

    document_id = calcular_document_id(texto_extraido)     # o la lista de páginas
    cantidad = indexar_documento(document_id, texto_extraido)

Si el documento ya está indexado con la configuración actual, no se vuelve a
calcular nada: no gasta cuota de Hugging Face (D-07).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

from . import errores as e
from .chunking import dividir_en_chunks
from .embeddings import EmbeddingsE5
from .errores import ErrorRAG
from .extraccion import extraer_paginas, texto_como_mcp
from .vectorstore import AlmacenChroma


def calcular_document_id(fuente: str | Sequence[str]) -> str:
    """
    Identidad del documento: los primeros 16 caracteres del SHA-256 de su texto.

    Acepta el `texto_extraido` del MCP o la lista de páginas: para el mismo
    archivo dan el mismo id, porque las páginas se unen igual que en el MCP.
    """
    texto = fuente.strip() if isinstance(fuente, str) else texto_como_mcp(fuente)
    if not texto:
        raise ErrorRAG(
            "El documento no tiene texto que se pueda procesar.",
            codigo=e.RAG_DOCUMENTO_VACIO,
            detalle="El texto extraído está vacío (¿un PDF escaneado sin capa de texto?).",
        )
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def indexar_documento(
    document_id: str,
    texto: str | Sequence[str],
    *,
    embeddings: EmbeddingsE5 | None = None,
    almacen: AlmacenChroma | None = None,
    forzar: bool = False,
) -> int:
    """
    Indexa el documento y devuelve la cantidad de chunks.

    `texto` es el texto extraído o, mejor, la lista de páginas (así cada chunk
    guarda su página). Si ya estaba indexado con la configuración actual, no
    hace nada y devuelve la cantidad existente; con `forzar=True` lo rehace.
    """
    if almacen is None or embeddings is None:
        from .servicios import almacen_por_defecto, embeddings_por_defecto

        almacen = almacen or almacen_por_defecto()
        embeddings = embeddings or embeddings_por_defecto()

    modelo = getattr(getattr(embeddings, "config", None), "modelo_embeddings", None)
    if modelo is not None and modelo != almacen.config.modelo_embeddings:
        raise ErrorRAG(
            "No se pudo indexar el documento.",
            codigo=e.RAG_INDICE,
            detalle=f"Los embeddings usan {modelo} y el índice espera {almacen.config.modelo_embeddings}.",
        )

    if not forzar and almacen.esta_indexado(document_id):
        return almacen.cantidad(document_id)

    chunks = dividir_en_chunks(texto, document_id, almacen.config)
    if not chunks:
        raise ErrorRAG(
            "El documento no tiene texto que se pueda indexar.",
            codigo=e.RAG_DOCUMENTO_VACIO,
            detalle="Después de normalizar no quedó ningún chunk útil.",
        )
    vectores = embeddings.embed_documents([c.texto for c in chunks])
    return almacen.guardar(document_id, chunks, vectores)


def indexar_archivo(
    ruta: str | Path,
    *,
    embeddings: EmbeddingsE5 | None = None,
    almacen: AlmacenChroma | None = None,
    forzar: bool = False,
) -> tuple[str, int]:
    """Atajo para scripts y pruebas: extrae por página, calcula el id e indexa."""
    paginas = extraer_paginas(ruta)
    document_id = calcular_document_id(paginas)
    cantidad = indexar_documento(document_id, paginas, embeddings=embeddings, almacen=almacen, forzar=forzar)
    return document_id, cantidad
