"""
NuevaMente — Modelos de datos del RAG.

  - `Chunk`: un fragmento del documento normalizado, listo para indexar.
  - `ChunkRecuperado`: lo que devuelve `recuperar()`. Es la interfaz acordada
    en el plan (§6): `chunk_id`, `texto`, `score` y `pagina`. La consumen el
    Investigador y el Redactor (que copia `chunk_id` en `anclaje`), y la
    fidelidad, que con `chunk_id` lee los vectores ya guardados en Chroma.

No viven en src/contracts/ porque no forman parte del JSON de salida: son la
interfaz entre carriles dentro del grafo. Para guardarlos en el estado del
grafo, `model_dump()` los convierte en diccionarios.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

#: chunk_id corto y estable dentro de un documento: c0001, c0002...
PATRON_CHUNK_ID = r"^c\d{4,}$"


def formatear_chunk_id(orden: int) -> str:
    """0 -> "c0001". Corto a propósito: el Redactor lo copia tal cual en `anclaje`."""
    return f"c{orden + 1:04d}"


class Chunk(BaseModel):
    """Un fragmento del documento normalizado, con su ubicación."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(pattern=PATRON_CHUNK_ID)
    document_id: str = Field(min_length=1)
    texto: str = Field(min_length=1)
    orden: int = Field(ge=0, description="Posición en el documento, desde 0.")
    inicio: int = Field(ge=0, description="Desplazamiento en caracteres dentro del texto normalizado.")
    pagina: int | None = Field(
        default=None, ge=1, description="Página donde empieza; None si la fuente no trae páginas."
    )
    pagina_fin: int | None = Field(default=None, ge=1, description="Página donde termina.")

    def metadatos(self) -> dict[str, str | int]:
        """Metadatos para Chroma, que no acepta valores None."""
        datos: dict[str, str | int] = {
            "document_id": self.document_id,
            "orden": self.orden,
            "inicio": self.inicio,
        }
        if self.pagina is not None:
            datos["pagina"] = self.pagina
        if self.pagina_fin is not None:
            datos["pagina_fin"] = self.pagina_fin
        return datos


class ChunkRecuperado(BaseModel):
    """Un chunk devuelto por `recuperar()`, con su similitud con la consulta."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    texto: str
    score: float = Field(ge=-1.0, le=1.0, description="Similitud coseno con la consulta.")
    pagina: int | None = None
    document_id: str | None = None
