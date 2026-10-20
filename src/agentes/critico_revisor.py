"""Adaptador LangGraph del agente Crítico/Revisor.

Envuelve el núcleo puro `revisar_contenido` como nodo del grafo. Recibe el
generador estructurado **inyectado** (decisión A3) y, opcionalmente, un
`calculador_fidelidad` (puerto hacia `src/fidelidad/`). No toca contadores:
`intentos_redactor` y `vueltas_modificacion` tienen un único dueño.

Firma esperada por `grafo.py`:

    nodo_revisor = construir_nodo_critico_revisor(generador)
    ...  builder.add_node("critico_revisor", nodo_revisor)
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from src.agent_state import AgentState
from src.agentes.agente_critico_revisor import CalculadorFidelidad, revisar_contenido
from src.contracts import ClaridadPedagogica, FormatoSalida
from src.errores import MENSAJE_POR_DEFECTO, ErrorSalidaInvalida, NuevaMenteError

NodoCriticoRevisor = Callable[[AgentState], Coroutine[Any, Any, dict]]


def _fallo(mensaje: str) -> dict[str, Any]:
    # No se puede juzgar claridad sin revisión; se marca como pendiente de revisión.
    return {
        "aprobado": False,
        "evaluacion_calidad": {
            "claridad_pedagogica": ClaridadPedagogica.REQUIERE_REVISION.value,
            "observaciones": mensaje,
        },
    }


def construir_nodo_critico_revisor(
    generador: Any,
    calculador_fidelidad: CalculadorFidelidad | None = None,
) -> NodoCriticoRevisor:
    """Devuelve el nodo que revisa el contenido y escribe `aprobado` y `evaluacion_calidad`."""

    async def nodo_critico_revisor(state: AgentState) -> dict:
        contenido = state.get("contenido_adaptado")
        if not contenido:
            return _fallo("No hay contenido generado para revisar.")

        formato_bruto = state.get("formato_salida")
        try:
            formato = FormatoSalida(formato_bruto)
        except (ValueError, TypeError):
            return _fallo(MENSAJE_POR_DEFECTO[ErrorSalidaInvalida.codigo])

        # Un canal nuevo vacío no debe revivir la evidencia legacy.
        if "chunks_fuente_estructurados" in state:
            chunks = state.get("chunks_fuente_estructurados")
        else:
            chunks = state.get("chunks_fuente_confirmados")

        try:
            resultado = await revisar_contenido(
                contenido=contenido,
                formato_salida=formato,
                chunks=chunks or [],
                generador=generador,
                calculador_fidelidad=calculador_fidelidad,
            )
        except NuevaMenteError as exc:
            return _fallo(MENSAJE_POR_DEFECTO[exc.codigo])
        except Exception:
            return _fallo(MENSAJE_POR_DEFECTO[ErrorSalidaInvalida.codigo])

        return {
            "aprobado": resultado.aprobado,
            "evaluacion_calidad": resultado.evaluacion_calidad,
        }

    return nodo_critico_revisor
