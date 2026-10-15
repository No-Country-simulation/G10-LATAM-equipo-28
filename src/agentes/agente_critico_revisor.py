"""Core desacoplado del agente Crítico/Revisor.

Revisa **formato primero y fidelidad cualitativa después**. Nunca reescribe el
contenido: aprueba o devuelve observaciones accionables para que el Redactor o
el Modificador corrijan.

El `anclaje_fuente_score` numérico NO lo calcula el LLM (decisión D-02). Este
core acepta un `CalculadorFidelidad` **inyectable** (opción A): si no se
inyecta, `evaluacion_calidad` queda solo con `claridad_pedagogica` y
`observaciones`. Así queda listo para enchufar `src/fidelidad/` (carril de
Oscar) sin tocar el agente.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Protocol, runtime_checkable

from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    ValidationError,
)

from src.agentes.agente_redactor_pedagogico import ChunkFuente
from src.agentes.redactor import adaptar_chunks_fuente
from src.contracts import ClaridadPedagogica, FormatoSalida
from src.errores import ErrorLLM, ErrorSalidaInvalida
from src.prompts.critico_revisor import construir_prompt_critico_revisor

TextoNoVacio = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]

#: Claves de fidelidad que el puerto puede aportar a `evaluacion_calidad`.
CLAVES_FIDELIDAD = (
    "anclaje_fuente_score",
    "afirmaciones_evaluadas",
    "afirmaciones_soportadas",
    "supero_umbral",
)

OBSERVACION_POR_DEFECTO = "Sin observaciones."


class RevisionOut(BaseModel):
    """Esquema estructurado que recibe el generador inyectado."""

    model_config = ConfigDict(extra="forbid")

    aprobado: bool
    claridad_pedagogica: ClaridadPedagogica
    observaciones: str = ""


class ResultadoRevision(BaseModel):
    """Resultado del Revisor, listo para escribir en el `AgentState`."""

    model_config = ConfigDict(extra="forbid")

    aprobado: bool
    evaluacion_calidad: dict[str, Any]


@runtime_checkable
class CalculadorFidelidad(Protocol):
    """Puerto hacia el verificador de fidelidad (p. ej. `src/fidelidad/`).

    Devuelve al menos `anclaje_fuente_score` (0..1); opcionalmente aporta
    `afirmaciones_evaluadas`, `afirmaciones_soportadas` y `supero_umbral`.
    No pasa por el LLM: es determinístico (similitud de embeddings).
    """

    def calcular(
        self, *, contenido: Mapping[str, Any], chunks: Sequence[ChunkFuente]
    ) -> Mapping[str, Any]:
        """Calcula las métricas de fidelidad del contenido contra los chunks."""


def _normalizar_contenido(contenido: Any) -> dict[str, Any]:
    if hasattr(contenido, "model_dump"):
        contenido = contenido.model_dump(mode="json")
    if not isinstance(contenido, Mapping):
        raise ErrorSalidaInvalida("Se requiere un contenido_adaptado para revisar.")
    if not contenido.get("items"):
        raise ErrorSalidaInvalida("El contenido a revisar no tiene items.")
    return dict(contenido)


def _evaluacion_base(revision: RevisionOut) -> dict[str, Any]:
    observaciones = revision.observaciones.strip() or OBSERVACION_POR_DEFECTO
    return {
        "claridad_pedagogica": revision.claridad_pedagogica.value,
        "observaciones": observaciones,
    }


def _aplicar_fidelidad(
    evaluacion: dict[str, Any],
    calculador: CalculadorFidelidad,
    contenido: Mapping[str, Any],
    fuentes: list[ChunkFuente],
) -> None:
    score = calculador.calcular(contenido=contenido, chunks=fuentes)
    if not isinstance(score, Mapping):
        raise ErrorSalidaInvalida("El calculador de fidelidad debe devolver un mapping.")
    for clave in CLAVES_FIDELIDAD:
        if clave in score:
            evaluacion[clave] = score[clave]
    # Decisión D-03: si la fidelidad quedó bajo el umbral, la claridad lo refleja.
    if score.get("supero_umbral") is False:
        evaluacion["claridad_pedagogica"] = ClaridadPedagogica.REQUIERE_REVISION.value


async def revisar_contenido(
    contenido: Mapping[str, Any] | Any,
    formato_salida: FormatoSalida,
    chunks: Sequence[Any],
    generador: Any,
    calculador_fidelidad: CalculadorFidelidad | None = None,
) -> ResultadoRevision:
    """Aprueba o rechaza el contenido generado, con observaciones accionables.

    `generador` cumple el protocolo `GeneradorEstructurado`
    (`async generate(*, prompt, output_model)`).
    """
    if not isinstance(formato_salida, FormatoSalida):
        raise ErrorSalidaInvalida("Se requiere un FormatoSalida válido para revisar.")
    contenido_dict = _normalizar_contenido(contenido)
    fuentes = adaptar_chunks_fuente(chunks)

    prompt = construir_prompt_critico_revisor(contenido_dict, formato_salida, fuentes)
    try:
        bruto = await generador.generate(prompt=prompt, output_model=RevisionOut)
    except ErrorLLM:
        raise
    except Exception as exc:
        raise ErrorLLM("Falló la revisión estructurada del Crítico/Revisor.") from exc

    try:
        revision = RevisionOut.model_validate(bruto)
    except (ValidationError, TypeError, ValueError) as exc:
        raise ErrorSalidaInvalida(f"La respuesta de revisión es inválida: {exc}") from exc

    evaluacion = _evaluacion_base(revision)
    if calculador_fidelidad is not None:
        _aplicar_fidelidad(evaluacion, calculador_fidelidad, contenido_dict, fuentes)

    return ResultadoRevision(aprobado=revision.aprobado, evaluacion_calidad=evaluacion)
