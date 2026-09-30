"""Frontera del Redactor para la orquestación, con dependencias inyectadas."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from src.agentes.agente_redactor_pedagogico import (
    ChunkFuente,
    EstadoRedactor,
    GeneradorEstructurado,
    redactar_pedagogicamente,
)
from src.contracts import (
    ContenidoAdaptado,
    MetadatosAprendizaje,
    NivelDetalle,
    PerfilDestinatario,
    SolicitudAdaptacion,
)
from src.errores import (
    ErrorParametro,
    ErrorSalidaInvalida,
    MENSAJE_POR_DEFECTO,
    NuevaMenteError,
)

StateRedactor = Mapping[str, Any]
ObtenerSolicitud = Callable[[StateRedactor], SolicitudAdaptacion]
PrepararPedagogia = Callable[[PerfilDestinatario, NivelDetalle], Any]
MENSAJE_ABSTENCION = "La evidencia disponible no permite redactar con respaldo."


def adaptar_chunks_fuente(chunks: Any) -> list[ChunkFuente]:
    """Proyecta DTOs RAG/investigador al core sin inventar IDs ni mutar el state.

    RAG expone chunk_id; el investigador y el core exponen id. Los metadatos
    RAG permanecen en el state original para fidelidad y persistencia.
    Los textos sin ID del stub actual deben sustituirse en la orquestación.
    """
    if chunks is None:
        return []
    if not isinstance(chunks, Sequence) or isinstance(chunks, (str, bytes)):
        raise ErrorSalidaInvalida("Se requiere una secuencia de chunks estructurados.")
    fuentes = []
    try:
        for chunk in chunks:
            datos = chunk.model_dump() if isinstance(chunk, BaseModel) else chunk
            if not isinstance(datos, Mapping):
                raise ErrorSalidaInvalida("Cada chunk requiere un ID original y texto.")
            if "id" in datos and "chunk_id" in datos and datos["id"] != datos["chunk_id"]:
                raise ErrorSalidaInvalida("El chunk contiene IDs contradictorios.")
            fuentes.append(ChunkFuente.model_validate({
                "id": datos.get("chunk_id", datos.get("id")),
                "texto": datos.get("texto"),
            }))
    except (ValidationError, TypeError, ValueError) as exc:
        raise ErrorSalidaInvalida("El chunk requiere un ID y texto válidos.") from exc
    if len({chunk.id for chunk in fuentes}) != len(fuentes):
        raise ErrorSalidaInvalida("Los IDs de chunks deben ser únicos.")
    return fuentes


class _GeneradorContado:
    """Cuenta únicamente llamadas de generación, sin introducir reintentos."""

    def __init__(self, generador: GeneradorEstructurado):
        self.generador = generador
        self.llamadas = 0

    async def generate(self, *, prompt: str, output_model: type[BaseModel]) -> Any:
        self.llamadas += 1
        return await self.generador.generate(prompt=prompt, output_model=output_model)


def _fallo(mensaje: str, intentos: int) -> dict[str, Any]:
    # Limpia una generación/revisión anterior para impedir que se persista.
    return {
        "contenido_adaptado": None,
        "metadatos": None,
        "evaluacion_calidad": None,
        "aprobado": False,
        "intentos_redactor": intentos,
        "status": "error",
        "error": mensaje,
    }


def construir_nodo_redactor(
    generador: GeneradorEstructurado,
    preparar_pedagogia: PrepararPedagogia,
    obtener_solicitud: ObtenerSolicitud,
):
    """Construye un nodo async que devuelve claves ya presentes en AgentState.

    obtener_solicitud entrega el documento y los parámetros validados por la
    composición. No se asumen campos de documento inexistentes en AgentState.
    preparar_pedagogia permite inyectar la función pública de pedagogía/PR #3.
    El caller debe usar enrutar_tras_redactor para detener errores/abstenciones.
    """
    async def nodo_redactor(state: StateRedactor) -> dict[str, Any]:
        intentos = state.get("intentos_redactor", 0)
        if type(intentos) is not int or intentos < 0:
            return _fallo(MENSAJE_POR_DEFECTO[ErrorParametro.codigo], 0)
        contado = _GeneradorContado(generador)
        try:
            if state.get("fuente_confirmada") is not True:
                return _fallo(MENSAJE_ABSTENCION, intentos)
            fuentes = adaptar_chunks_fuente(state.get("chunks_fuente_confirmados"))
            if not fuentes:
                return _fallo(MENSAJE_ABSTENCION, intentos)
            solicitud = obtener_solicitud(state)
            if not isinstance(solicitud, SolicitudAdaptacion):
                raise ErrorParametro("Se requiere una solicitud validada.")
            # Revalida incluso modelos construidos sin validación por un caller.
            solicitud = SolicitudAdaptacion.model_validate(solicitud.model_dump())
            spec = preparar_pedagogia(solicitud.perfil_destinatario, solicitud.nivel_detalle)
            resultado = await redactar_pedagogicamente(
                solicitud=solicitud,
                chunks=fuentes,
                especificacion_pedagogica=spec,
                generador=contado,
                feedback_revisor=state.get("evaluacion_calidad") if intentos else None,
            )
            if resultado.estado is EstadoRedactor.EVIDENCIA_INSUFICIENTE:
                return _fallo(MENSAJE_ABSTENCION, intentos + contado.llamadas)
            contenido = resultado.contenido
            assert contenido is not None
            salida = ContenidoAdaptado(
                titulo=contenido.titulo,
                introduccion_contextualizada=contenido.introduccion_contextualizada,
                items=[item.model_dump(mode="json") for item in contenido.items],
            )
            metadatos = MetadatosAprendizaje(
                perfil_aplicado=solicitud.perfil_destinatario,
                formato_generado=solicitud.formato_salida,
                nicho_aplicado=solicitud.nicho_sector,
                nivel_detalle_aplicado=solicitud.nivel_detalle,
                tiempo_estimado_estudio_minutos=contenido.tiempo_estimado_estudio_minutos,
                conceptos_clave=contenido.conceptos_clave,
                prerrequisitos=contenido.prerrequisitos,
            )
            return {
                "contenido_adaptado": salida.model_dump(mode="json"),
                "metadatos": metadatos.model_dump(mode="json"),
                "intentos_redactor": intentos + contado.llamadas,
                "evaluacion_calidad": None,
                "aprobado": None,
                "error": None,
            }
        except NuevaMenteError as exc:
            return _fallo(MENSAJE_POR_DEFECTO[exc.codigo], intentos + contado.llamadas)
        except ValidationError:
            return _fallo(MENSAJE_POR_DEFECTO[ErrorParametro.codigo], intentos + contado.llamadas)
        except Exception:
            return _fallo(MENSAJE_POR_DEFECTO[ErrorSalidaInvalida.codigo], intentos + contado.llamadas)

    return nodo_redactor


def enrutar_tras_redactor(state: StateRedactor) -> Literal["critico_revisor", "error"]:
    """Expone la ruta para que grafo detenga una generación fallida antes del juez."""
    if state.get("error") or not state.get("contenido_adaptado"):
        return "error"
    return "critico_revisor"
