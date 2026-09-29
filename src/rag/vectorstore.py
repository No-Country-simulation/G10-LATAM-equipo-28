"""
NuevaMente — Índice vectorial en Chroma: una colección por `document_id` (D-07).

  - Persistente en CHROMA_PATH (por defecto, chroma_db/ en la raíz del repo,
    ignorada por git).
  - Distancia coseno. Chroma usa la euclidiana si no se le indica.
  - Sin telemetría y sin el modelo de embeddings por defecto de Chroma: los
    vectores siempre llegan hechos desde EmbeddingsE5. Si faltaran, Chroma
    intentaría descargar su propio modelo (verificado con chromadb 1.5.9).
  - Cada colección guarda la «firma» de cómo se indexó (versión del índice,
    modelo, dimensión y chunking). Si la configuración cambia, el índice viejo
    deja de servir y se rehace.
  - `get()` de Chroma no respeta el orden de los ids pedidos: aquí se reordena.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from . import errores as e
from .configuracion import ConfigRAG, cargar_config
from .errores import ErrorRAG
from .modelos import Chunk

#: Súbela si cambian la normalización o el chunking de forma que el índice
#: viejo ya no sirva: todos los documentos se reindexan solos.
VERSION_INDICE = 1

PREFIJO_COLECCION = "doc_"
_PATRON_DOCUMENT_ID = re.compile(r"^[A-Za-z0-9_-]{1,60}$")
_TAMANO_BLOQUE_ALTA = 500


def firma_de(config: ConfigRAG) -> str:
    """Resume lo que hace incompatible un índice con otro."""
    return (
        f"v{VERSION_INDICE}|{config.modelo_embeddings}|{config.dimension_embeddings}|"
        f"{config.chunk_size}|{config.chunk_overlap}|{config.chunk_minimo}"
    )


@dataclass(frozen=True)
class Coincidencia:
    """Un resultado de `consultar()`: el chunk y su similitud coseno con la consulta."""

    chunk_id: str
    texto: str
    score: float
    metadatos: dict[str, Any] = field(default_factory=dict)


class AlmacenChroma:
    """Guarda y consulta los chunks de cada documento en su propia colección."""

    def __init__(self, config: ConfigRAG | None = None, *, cliente: Any = None) -> None:
        self.config = config if config is not None else cargar_config()
        self._cliente = cliente

    # ------------------------------------------------------------------
    # Cliente y colecciones
    # ------------------------------------------------------------------

    @property
    def cliente(self) -> Any:
        if self._cliente is None:
            import chromadb  # import diferido: pesa y no hace falta hasta indexar
            from chromadb.config import Settings

            self.config.chroma_path.mkdir(parents=True, exist_ok=True)
            self._cliente = chromadb.PersistentClient(
                path=str(self.config.chroma_path),
                settings=Settings(anonymized_telemetry=False),
            )
        return self._cliente

    @staticmethod
    def nombre_coleccion(document_id: str) -> str:
        if not _PATRON_DOCUMENT_ID.match(document_id or ""):
            raise ErrorRAG(
                "El identificador del documento no es válido.",
                codigo=e.RAG_INDICE,
                detalle=f"document_id {document_id!r}: se esperan letras, números, _ o -.",
            )
        return f"{PREFIJO_COLECCION}{document_id}"

    def _coleccion(self, document_id: str) -> Any | None:
        from chromadb.errors import NotFoundError

        try:
            return self.cliente.get_collection(self.nombre_coleccion(document_id), embedding_function=None)
        except NotFoundError:
            return None

    def _coleccion_obligatoria(self, document_id: str) -> Any:
        coleccion = self._coleccion(document_id)
        if coleccion is None:
            raise ErrorRAG(
                "El documento todavía no está indexado.",
                codigo=e.RAG_DOCUMENTO_NO_INDEXADO,
                detalle=f"No hay colección para el document_id {document_id}.",
            )
        return coleccion

    # ------------------------------------------------------------------
    # Consultas sobre el estado del índice
    # ------------------------------------------------------------------

    def esta_indexado(self, document_id: str) -> bool:
        """True si el documento tiene chunks indexados con la configuración actual."""
        coleccion = self._coleccion(document_id)
        if coleccion is None or coleccion.count() == 0:
            return False
        return (coleccion.metadata or {}).get("firma") == firma_de(self.config)

    def cantidad(self, document_id: str) -> int:
        coleccion = self._coleccion(document_id)
        return 0 if coleccion is None else coleccion.count()

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def guardar(self, document_id: str, chunks: Sequence[Chunk], vectores: Sequence[Sequence[float]]) -> int:
        """
        Crea (o rehace) la colección del documento con sus chunks y vectores.

        Devuelve la cantidad de chunks guardados.
        """
        if not chunks:
            raise ErrorRAG(
                "El documento no tiene texto que se pueda indexar.",
                codigo=e.RAG_DOCUMENTO_VACIO,
            )
        if len(chunks) != len(vectores):
            raise ErrorRAG(
                "No se pudo indexar el documento.",
                codigo=e.RAG_INDICE,
                detalle=f"{len(chunks)} chunks y {len(vectores)} vectores: deberían ser iguales.",
            )
        ajenos = {c.document_id for c in chunks} - {document_id}
        if ajenos:
            raise ErrorRAG(
                "No se pudo indexar el documento.",
                codigo=e.RAG_INDICE,
                detalle=f"Hay chunks de otros documentos: {sorted(ajenos)}.",
            )
        dimension = self.config.dimension_embeddings
        if any(len(v) != dimension for v in vectores):
            raise ErrorRAG(
                "No se pudo indexar el documento.",
                codigo=e.RAG_INDICE,
                detalle=f"Todos los vectores deben tener dimensión {dimension}.",
            )

        self.borrar(document_id)  # rehacer desde cero: nunca se mezclan dos versiones
        coleccion = self.cliente.create_collection(
            self.nombre_coleccion(document_id),
            configuration={"hnsw": {"space": "cosine"}},
            embedding_function=None,
            metadata={
                "document_id": document_id,
                "firma": firma_de(self.config),
                "chunks": len(chunks),
                "indexado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
        )
        for inicio in range(0, len(chunks), _TAMANO_BLOQUE_ALTA):
            bloque = chunks[inicio : inicio + _TAMANO_BLOQUE_ALTA]
            coleccion.add(
                ids=[c.chunk_id for c in bloque],
                embeddings=[list(map(float, v)) for v in vectores[inicio : inicio + _TAMANO_BLOQUE_ALTA]],
                documents=[c.texto for c in bloque],
                metadatas=[c.metadatos() for c in bloque],
            )
        return coleccion.count()

    def borrar(self, document_id: str) -> bool:
        """Borra el índice de un documento (no toca ningún archivo del usuario)."""
        if self._coleccion(document_id) is None:
            return False
        self.cliente.delete_collection(self.nombre_coleccion(document_id))
        return True

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def consultar(self, document_id: str, vector: Sequence[float], top_k: int) -> list[Coincidencia]:
        """Los `top_k` chunks más parecidos al vector, de mayor a menor similitud."""
        coleccion = self._coleccion_obligatoria(document_id)
        total = coleccion.count()
        if total == 0 or top_k < 1:
            return []
        respuesta = coleccion.query(
            query_embeddings=[list(map(float, vector))],
            n_results=min(top_k, total),
            include=["documents", "metadatas", "distances"],
        )
        coincidencias = []
        for chunk_id, texto, metadatos, distancia in zip(
            respuesta["ids"][0],
            respuesta["documents"][0],
            respuesta["metadatas"][0],
            respuesta["distances"][0],
            strict=True,
        ):
            similitud = max(-1.0, min(1.0, 1.0 - float(distancia)))  # distancia coseno = 1 - similitud
            coincidencias.append(Coincidencia(chunk_id, texto, similitud, dict(metadatos or {})))
        return coincidencias

    def vectores_de_chunks(self, document_id: str, chunk_ids: Sequence[str]) -> list[list[float]]:
        """Los vectores guardados de esos chunks, en el mismo orden en que se piden."""
        if not chunk_ids:
            return []
        coleccion = self._coleccion_obligatoria(document_id)
        respuesta = coleccion.get(ids=list(dict.fromkeys(chunk_ids)), include=["embeddings"])
        por_id = {
            chunk_id: [float(x) for x in vector]
            for chunk_id, vector in zip(respuesta["ids"], respuesta["embeddings"], strict=True)
        }
        faltantes = [c for c in chunk_ids if c not in por_id]
        if faltantes:
            raise ErrorRAG(
                "Uno de los fragmentos citados no existe en el documento.",
                codigo=e.RAG_CHUNK_NO_ENCONTRADO,
                detalle=f"No están en {document_id}: {faltantes}.",
            )
        return [por_id[c] for c in chunk_ids]
