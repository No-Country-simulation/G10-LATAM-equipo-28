"""Adaptador LangGraph del agente Investigador.

Envuelve el núcleo puro `investigar` (en `agente_investigador.py`) como nodo del
grafo. Recibe el `recuperador` (vector store, p. ej. Chroma) y el `generador`
(LLM para redactar la aclaración) **inyectados**: la elección del vector store y
del proveedor vive en el cableado (`app.py`), no acá. Por eso este archivo no
nombra ningún proveedor de LLM.

Firma esperada por `grafo.py`:

    nodo_investigador = construir_nodo_investigador(recuperador, generador)
    ...  builder.add_node("investigador", nodo_investigador)
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from src.agent_state import AgentState
from src.agentes.agente_investigador import (
    UMBRAL_COBERTURA,
    Recuperador,
    ResultadoInvestigador,
    investigar,
)
from src.agentes.protocolos import GeneradorEstructurado
from src.errores import MENSAJE_POR_DEFECTO, CodigoError, NuevaMenteError

NodoInvestigador = Callable[[AgentState], Coroutine[Any, Any, dict]]


def _chunks_estructurados(resultado: ResultadoInvestigador) -> list[dict[str, Any]]:
    """Serializa los chunks confirmados al canal aditivo del `AgentState`."""
    return [chunk.model_dump(mode="json") for chunk in resultado.chunks_fuente_confirmados]


def _sin_cobertura(
    *, mensaje_aclaracion: str | None, error: str | None = None
) -> dict[str, Any]:
    """Estado seguro cuando el tema no está cubierto (o el nodo falló).

    El canal estructurado se limpia a `[]` para no revivir evidencia de una
    ejecución anterior (regla del Redactor).
    """
    salida: dict[str, Any] = {
        "fuente_confirmada": False,
        "chunks_fuente_confirmados": [],
        "chunks_fuente_estructurados": [],
        "mensaje_aclaracion": mensaje_aclaracion,
    }
    if error is not None:
        salida["status"] = "error"
        salida["error"] = error
    return salida


def construir_nodo_investigador(
    recuperador: Recuperador,
    generador: GeneradorEstructurado,
    *,
    umbral: float = UMBRAL_COBERTURA,
    top_k: int = 5,
) -> NodoInvestigador:
    """Devuelve el nodo que verifica cobertura y escribe el estado del RAG.

    Escribe las mismas claves que el stub del grafo (`fuente_confirmada`,
    `chunks_fuente_confirmados`, `mensaje_aclaracion`) más el canal estructurado
    `chunks_fuente_estructurados` que consume el Redactor. No inventa contenido:
    delega toda la decisión en el núcleo `investigar`.
    """

    async def nodo_investigador(state: AgentState) -> dict:
        tema = state.get("tema_consulta") or state.get("tema_pedido_chat") or ""
        titulo = state.get("documento_titulo") or ""
        try:
            resultado = await investigar(
                tema,
                recuperador,
                generador,
                titulo,
                umbral=umbral,
                top_k=top_k,
            )
        except NuevaMenteError as exc:
            return _sin_cobertura(mensaje_aclaracion=None, error=exc.mensaje_usuario)
        except Exception:
            return _sin_cobertura(
                mensaje_aclaracion=None,
                error=MENSAJE_POR_DEFECTO[CodigoError.ERROR_INTERNO],
            )

        if resultado.fuente_confirmada:
            return {
                "fuente_confirmada": True,
                "chunks_fuente_confirmados": [
                    chunk.id for chunk in resultado.chunks_fuente_confirmados
                ],
                "chunks_fuente_estructurados": _chunks_estructurados(resultado),
                "mensaje_aclaracion": None,
            }

        return _sin_cobertura(mensaje_aclaracion=resultado.mensaje_aclaracion)

    return nodo_investigador
