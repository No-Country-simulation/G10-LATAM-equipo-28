"""Adaptador del RAG al protocolo `Recuperador` del Investigador.

Es el cable que faltaba: conecta `rag.recuperacion.recuperar()` (el índice
vectorial real, de Oscar) con el nodo Investigador, que solo conoce el protocolo

    Recuperador.buscar(consulta, top_k) -> list[ChunkConScore]

El índice está particionado por documento, así que el adaptador necesita saber
**cuál** documento buscar. Ese id lo escribe el nodo Ingesta en el `AgentState`
(ver `document_id`); el nodo Investigador se lo pasa con `fijar_documento()`
antes de buscar (ver `agentes/investigador.py`). Sin documento fijado, `buscar()`
falla con `RAG_DOCUMENTO_NO_INDEXADO` en vez de buscar en el vacío.

Los embeddings y el almacén se inyectan (por defecto, los del `.env` vía
`rag.servicios`), igual que en el resto del carril: el agente no elige
proveedores ni vector stores.
"""

from __future__ import annotations

from typing import Any

from src.agentes.agente_investigador import ChunkConScore
from src.rag.errores import RAG_DOCUMENTO_NO_INDEXADO, ErrorRAG
from src.rag.recuperacion import recuperar


class RecuperadorRAG:
    """Implementa el protocolo `Recuperador` sobre `rag.recuperacion.recuperar()`.

    `top_k` y `umbral` son opcionales: si no se indican, `recuperar()` usa los
    del `.env` (configuración del RAG). Se permite fijarlos para pruebas.
    """

    def __init__(
        self,
        document_id: str | None = None,
        *,
        top_k: int | None = None,
        umbral: float | None = None,
        embeddings: Any = None,
        almacen: Any = None,
    ) -> None:
        self._document_id = document_id
        self._top_k = top_k
        self._umbral = umbral
        self._embeddings = embeddings
        self._almacen = almacen

    @property
    def document_id(self) -> str | None:
        return self._document_id

    def fijar_documento(self, document_id: str | None) -> None:
        """Ata el recuperador al documento activo. Lo llama el nodo Investigador."""
        self._document_id = document_id

    def buscar(self, consulta: str, top_k: int = 5) -> list[ChunkConScore]:
        """Chunks del documento activo relevantes a la consulta, con su similitud."""
        if not self._document_id:
            raise ErrorRAG(
                "Todavía no hay un documento indexado sobre el cual buscar.",
                codigo=RAG_DOCUMENTO_NO_INDEXADO,
                detalle="El nodo Ingesta no fijó un document_id antes del Investigador.",
            )

        k = top_k if self._top_k is None else self._top_k
        chunks = recuperar(
            self._document_id,
            consulta,
            top_k=k,
            umbral=self._umbral,
            embeddings=self._embeddings,
            almacen=self._almacen,
        )
        return [
            ChunkConScore(id=chunk.chunk_id, texto=chunk.texto, score=chunk.score)
            for chunk in chunks
        ]
