"""Agente Investigador: verifica si el tema pedido está cubierto en el documento.

La búsqueda es determinística (Chroma) y se inyecta vía el protocolo
`Recuperador`; el LLM solo redacta el mensaje de aclaración cuando NO hay
cobertura. El agente no accede a OCI y nunca inventa contenido: el mensaje se
ancla al título/resumen del documento.
"""

from __future__ import annotations

from typing import Annotated, Protocol, runtime_checkable

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

from src.errores import ErrorLLM, ErrorSalidaInvalida
from src.prompts.investigador import construir_prompt_investigador

from .protocolos import GeneradorEstructurado

TextoNoVacio = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]

#: Similitud mínima para considerar que un chunk cubre el tema (spec de la bóveda).
UMBRAL_COBERTURA = 0.78


class ChunkConScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: TextoNoVacio
    texto: TextoNoVacio
    score: float = Field(ge=0.0, le=1.0)


@runtime_checkable
class Recuperador(Protocol):
    """Buscador de chunks en el vector store (lo implementa `rag/vectorstore.py`)."""

    def buscar(self, consulta: str, top_k: int = 5) -> list[ChunkConScore]:
        """Devuelve los chunks más similares a la consulta, con su similitud."""


class MensajeAclaracion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mensaje: TextoNoVacio


class ResultadoInvestigador(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fuente_confirmada: bool
    chunks_fuente_confirmados: list[ChunkConScore] = Field(default_factory=list)
    mensaje_aclaracion: str | None = None

    @model_validator(mode="after")
    def _coherencia(self) -> "ResultadoInvestigador":
        if self.fuente_confirmada and not self.chunks_fuente_confirmados:
            raise ValueError("fuente_confirmada=True exige chunks_fuente_confirmados.")
        if not self.fuente_confirmada and not self.mensaje_aclaracion:
            raise ValueError("fuente_confirmada=False exige un mensaje_aclaracion.")
        return self


async def investigar(
    tema_consulta: str,
    recuperador: Recuperador,
    generador: GeneradorEstructurado,
    titulo_documento: str,
    resumen_documento: str | None = None,
    umbral: float = UMBRAL_COBERTURA,
    top_k: int = 5,
) -> ResultadoInvestigador:
    """Confirma cobertura del tema o devuelve un mensaje de aclaración."""
    tema = (tema_consulta or "").strip()
    if not tema:
        raise ErrorSalidaInvalida("El Investigador requiere un tema_consulta no vacío.")

    try:
        recuperados = [ChunkConScore.model_validate(c) for c in recuperador.buscar(tema, top_k)]
    except (ValidationError, TypeError) as exc:
        raise ErrorSalidaInvalida("Los chunks recuperados no son válidos.") from exc

    relevantes = [chunk for chunk in recuperados if chunk.score >= umbral]
    if relevantes:
        return ResultadoInvestigador(
            fuente_confirmada=True,
            chunks_fuente_confirmados=relevantes,
        )

    prompt = construir_prompt_investigador(tema, titulo_documento, resumen_documento)
    try:
        bruto = await generador.generate(prompt=prompt, output_model=MensajeAclaracion)
    except ErrorLLM:
        raise
    except Exception as exc:
        raise ErrorLLM(
            "Falló la redacción del mensaje de aclaración del Investigador."
        ) from exc

    try:
        salida = MensajeAclaracion.model_validate(bruto)
    except (ValidationError, TypeError, ValueError) as exc:
        raise ErrorSalidaInvalida(
            f"El mensaje de aclaración no cumple el contrato: {exc}"
        ) from exc

    return ResultadoInvestigador(
        fuente_confirmada=False,
        mensaje_aclaracion=salida.mensaje,
    )
