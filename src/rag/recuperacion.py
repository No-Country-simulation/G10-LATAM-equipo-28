"""
NuevaMente — Recuperación: lo que el RAG le entrega a los demás carriles.

    recuperar(document_id, consulta)        -> list[ChunkRecuperado]   Investigador, Redactor
    embeder_consultas(textos)               -> vectores "query: "      Revisor (fidelidad)
    vectores_de_chunks(document_id, ids)    -> vectores ya guardados   Revisor (fidelidad)

`recuperar()` devuelve los RETRIEVAL_TOP_K chunks más parecidos que superan
UMBRAL_RETRIEVAL, de mayor a menor. Si ninguno lo supera, devuelve una lista
vacía: decidir la ronda de aclaración le toca al Investigador.

`vectores_de_chunks()` existe para que la fidelidad no vuelva a pagar los
embeddings de los chunks: ya están en Chroma.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import errores as e
from .embeddings import EmbeddingsE5
from .errores import ErrorRAG
from .modelos import ChunkRecuperado
from .vectorstore import AlmacenChroma


def _dependencias(
    embeddings: EmbeddingsE5 | None, almacen: AlmacenChroma | None
) -> tuple[EmbeddingsE5, AlmacenChroma]:
    from .servicios import almacen_por_defecto, embeddings_por_defecto

    return embeddings or embeddings_por_defecto(), almacen or almacen_por_defecto()


def recuperar(
    document_id: str,
    consulta: str,
    *,
    top_k: int | None = None,
    umbral: float | None = None,
    embeddings: EmbeddingsE5 | None = None,
    almacen: AlmacenChroma | None = None,
) -> list[ChunkRecuperado]:
    """Chunks del documento que responden a la consulta, filtrados por umbral."""
    if not isinstance(consulta, str) or not consulta.strip():
        raise ErrorRAG(
            "Escribe qué quieres buscar en el documento.",
            codigo=e.RAG_CONSULTA_VACIA,
        )
    if almacen is None or embeddings is None:
        embeddings, almacen = _dependencias(embeddings, almacen)

    if not almacen.esta_indexado(document_id):
        raise ErrorRAG(
            "El documento todavía no está indexado.",
            codigo=e.RAG_DOCUMENTO_NO_INDEXADO,
            detalle=f"Indexa {document_id} antes de consultarlo (o la configuración cambió).",
        )

    cfg = almacen.config
    k = cfg.top_k if top_k is None else top_k
    minimo = cfg.umbral_retrieval if umbral is None else umbral
    vector = embeddings.embed_query(consulta)
    return [
        ChunkRecuperado(
            chunk_id=c.chunk_id,
            texto=c.texto,
            score=c.score,
            pagina=c.metadatos.get("pagina"),
            document_id=document_id,
        )
        for c in almacen.consultar(document_id, vector, k)
        if c.score >= minimo
    ]


def embeder_consultas(textos: Sequence[str], *, embeddings: EmbeddingsE5 | None = None) -> list[list[float]]:
    """Vectores "query: " para las afirmaciones que verifica la fidelidad."""
    if embeddings is None:
        embeddings, _ = _dependencias(None, None)
    return embeddings.embeder_consultas(textos)


def vectores_de_chunks(
    document_id: str, chunk_ids: Sequence[str], *, almacen: AlmacenChroma | None = None
) -> list[list[float]]:
    """Vectores ya guardados en Chroma, en el mismo orden que `chunk_ids`."""
    if almacen is None:
        from .servicios import almacen_por_defecto

        almacen = almacen_por_defecto()
    return almacen.vectores_de_chunks(document_id, chunk_ids)
