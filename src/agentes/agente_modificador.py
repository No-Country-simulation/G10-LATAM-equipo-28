"""Core desacoplado del agente Modificador.

Aplica un cambio **puntual** sobre el `contenido_adaptado` ya aprobado, sin
regenerar el resto. Reutiliza el schema (`ContenidoRedactor`), la respuesta
estructurada (`RespuestaGenerador`) y la validación de anchors del Redactor:
las reglas de fidelidad deben ser exactamente las mismas, no una copia que
pueda divergir.

La redacción del prompt de modificación es la única pieza que no venía cerrada
en la spec; su texto está documentado en `src/prompts/modificador.py`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from src.agentes.agente_redactor_pedagogico import (
    ChunkFuente,
    EstadoRedactor,
    GeneradorEstructurado,
    RespuestaGenerador,
    ResultadoRedactor,
    _normalizar_chunks,
    _validar_items,
)
from src.contracts import FORMATOS_IMPLEMENTADOS_MVP, SolicitudAdaptacion
from src.errores import ErrorFormatoNoDisponible, ErrorLLM, ErrorSalidaInvalida
from src.prompts.modificador import construir_prompt_modificador


def _normalizar_contenido(contenido: Any) -> dict[str, Any]:
    if hasattr(contenido, "model_dump"):
        contenido = contenido.model_dump(mode="json")
    if not isinstance(contenido, Mapping):
        raise ErrorSalidaInvalida("El Modificador requiere un contenido_adaptado.")
    if not contenido.get("items"):
        raise ErrorSalidaInvalida("El contenido a modificar no tiene items.")
    return dict(contenido)


async def modificar_contenido(
    solicitud: SolicitudAdaptacion,
    chunks: Sequence[ChunkFuente | Mapping[str, Any]],
    contenido_actual: Mapping[str, Any] | Any,
    instruccion_modificacion: str,
    especificacion_pedagogica: Any,
    generador: GeneradorEstructurado,
) -> ResultadoRedactor:
    """Aplica el cambio pedido y valida formato e integridad de anchors."""
    if not isinstance(solicitud, SolicitudAdaptacion):
        raise ErrorSalidaInvalida("Se requiere una SolicitudAdaptacion validada.")
    if solicitud.formato_salida not in FORMATOS_IMPLEMENTADOS_MVP:
        raise ErrorFormatoNoDisponible(
            f"El formato '{solicitud.formato_salida.value}' no está disponible en esta fase.",
            campo="formato_salida",
            valores_admitidos=sorted(f.value for f in FORMATOS_IMPLEMENTADOS_MVP),
        )

    instruccion = (instruccion_modificacion or "").strip()
    if not instruccion:
        raise ErrorSalidaInvalida("El Modificador requiere una instrucción de modificación.")
    contenido_previo = _normalizar_contenido(contenido_actual)
    fuentes = _normalizar_chunks(chunks)
    if not fuentes:
        return ResultadoRedactor(
            estado=EstadoRedactor.EVIDENCIA_INSUFICIENTE,
            motivo_abstencion="No se recibieron chunks de fuente para respaldar la modificación.",
        )

    try:
        prompt = construir_prompt_modificador(
            solicitud, fuentes, especificacion_pedagogica, contenido_previo, instruccion
        )
    except (TypeError, ValueError) as exc:
        raise ErrorSalidaInvalida(f"No se pudo construir el prompt: {exc}") from exc

    try:
        bruto = await generador.generate(prompt=prompt, output_model=RespuestaGenerador)
    except ErrorLLM:
        raise
    except Exception as exc:
        raise ErrorLLM("Falló la modificación estructurada del Modificador.") from exc

    try:
        generado = RespuestaGenerador.model_validate(bruto)
    except (ValidationError, TypeError, ValueError) as exc:
        raise ErrorSalidaInvalida(f"La respuesta estructurada es inválida: {exc}") from exc

    if generado.estado is EstadoRedactor.EVIDENCIA_INSUFICIENTE:
        return ResultadoRedactor(
            estado=generado.estado,
            motivo_abstencion=generado.motivo_abstencion,
        )

    assert generado.contenido is not None  # garantizado por RespuestaGenerador
    items_raw = [item.model_dump(mode="json") for item in generado.contenido.items]
    items = _validar_items(solicitud, items_raw, {chunk.id for chunk in fuentes})
    contenido = generado.contenido.model_copy(update={"items": items})
    return ResultadoRedactor(estado=generado.estado, contenido=contenido)
