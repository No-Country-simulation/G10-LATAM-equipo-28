"""Adaptador LangGraph del agente Modificador.

Envuelve el núcleo puro `modificar_contenido` como nodo del grafo. Recibe el
generador, la pedagogía y el validador de solicitud **inyectados** (decisión A3),
igual que el Redactor.

Escribe `contenido_adaptado` y `vueltas_modificacion = valor + 1` (nunca
resetea). Si la modificación falla, **no borra** el contenido ya aprobado: lo
deja intacto y reporta el error, para no perder el artefacto.

Firma esperada por `grafo.py`:

    nodo_modificador = construir_nodo_modificador(generador, preparar_pedagogia, obtener_solicitud)
    ...  builder.add_node("modificador", nodo_modificador)
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine, Mapping
from typing import Any

from pydantic import ValidationError

from src.agent_state import AgentState
from src.agentes.agente_modificador import modificar_contenido
from src.agentes.agente_redactor_pedagogico import (
    EstadoRedactor,
    GeneradorEstructurado,
)
from src.agentes.redactor import MENSAJE_ABSTENCION, adaptar_chunks_fuente
from src.contracts import ContenidoAdaptado, SolicitudAdaptacion
from src.errores import (
    ErrorParametro,
    ErrorSalidaInvalida,
    MENSAJE_POR_DEFECTO,
    NuevaMenteError,
)

NodoModificador = Callable[[AgentState], Coroutine[Any, Any, dict]]
PrepararPedagogia = Callable[..., Any]
ObtenerSolicitud = Callable[[Mapping[str, Any]], SolicitudAdaptacion]


def construir_nodo_modificador(
    generador: GeneradorEstructurado,
    preparar_pedagogia: PrepararPedagogia,
    obtener_solicitud: ObtenerSolicitud,
) -> NodoModificador:
    """Devuelve el nodo que aplica el cambio pedido sobre el contenido aprobado."""

    async def nodo_modificador(state: AgentState) -> dict:
        vueltas = state.get("vueltas_modificacion", 0)
        if type(vueltas) is not int or vueltas < 0:
            return {
                "vueltas_modificacion": 0,
                "error": MENSAJE_POR_DEFECTO[ErrorParametro.codigo],
            }

        def _fallo(mensaje: str) -> dict[str, Any]:
            # Incrementa siempre para que el tope de vueltas sea alcanzable;
            # no incluye contenido_adaptado para no borrar lo ya aprobado.
            return {"vueltas_modificacion": vueltas + 1, "error": mensaje}

        contenido_actual = state.get("contenido_adaptado")
        if not contenido_actual:
            return _fallo("No hay contenido aprobado que modificar.")

        instruccion = (state.get("instruccion_modificacion") or "").strip()
        if not instruccion:
            return _fallo("No se recibió una instrucción de modificación.")

        if "chunks_fuente_estructurados" in state:
            chunks = state.get("chunks_fuente_estructurados")
        else:
            chunks = state.get("chunks_fuente_confirmados")

        try:
            fuentes = adaptar_chunks_fuente(chunks)
            solicitud = obtener_solicitud(state)
            if not isinstance(solicitud, SolicitudAdaptacion):
                raise ErrorParametro("Se requiere una solicitud validada.")
            solicitud = SolicitudAdaptacion.model_validate(solicitud.model_dump())
            spec = preparar_pedagogia(solicitud.perfil_destinatario, solicitud.nivel_detalle)
            resultado = await modificar_contenido(
                solicitud=solicitud,
                chunks=fuentes,
                contenido_actual=contenido_actual,
                instruccion_modificacion=instruccion,
                especificacion_pedagogica=spec,
                generador=generador,
            )
            if resultado.estado is EstadoRedactor.EVIDENCIA_INSUFICIENTE:
                return _fallo(MENSAJE_ABSTENCION)
            contenido = resultado.contenido
            assert contenido is not None
            salida = ContenidoAdaptado(
                titulo=contenido.titulo,
                introduccion_contextualizada=contenido.introduccion_contextualizada,
                items=[item.model_dump(mode="json") for item in contenido.items],
            )
            return {
                "contenido_adaptado": salida.model_dump(mode="json"),
                "vueltas_modificacion": vueltas + 1,
                "aprobado": None,
                "evaluacion_calidad": None,
                "error": None,
            }
        except NuevaMenteError as exc:
            return _fallo(MENSAJE_POR_DEFECTO[exc.codigo])
        except ValidationError:
            return _fallo(MENSAJE_POR_DEFECTO[ErrorParametro.codigo])
        except Exception:
            return _fallo(MENSAJE_POR_DEFECTO[ErrorSalidaInvalida.codigo])

    return nodo_modificador
