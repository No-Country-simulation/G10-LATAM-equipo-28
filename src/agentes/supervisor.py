"""Adaptador LangGraph del agente Supervisor.

Envuelve el núcleo puro `clasificar_intencion` (en `agente_supervisor.py`) como
nodo del grafo. Recibe el generador estructurado **inyectado** (decisión A3): la
elección de proveedor, del cliente y del rate limiter vive en el cableado
(`app.py`), no acá. Por eso este archivo no nombra ningún proveedor de LLM.

Firma esperada por `grafo.py`:

    nodo_supervisor = construir_nodo_supervisor(generador)
    ...  builder.add_node("supervisor", nodo_supervisor)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Coroutine

from src.agent_state import AgentState
from src.agentes.agente_supervisor import clasificar_intencion
from src.agentes.protocolos import GeneradorEstructurado

NodoSupervisor = Callable[[AgentState], Coroutine[Any, Any, dict]]


def _texto_mensaje(mensaje: Any) -> str:
    """Extrae el texto de un mensaje, venga como dict o como objeto de LangChain."""
    if isinstance(mensaje, dict):
        return str(mensaje.get("content") or "")
    return str(getattr(mensaje, "content", "") or "")


def _ultimo_mensaje_usuario(mensajes: list[Any]) -> str:
    """Devuelve el texto del último mensaje del usuario.

    Los mensajes del estado son de `langgraph.graph.message.add_messages`, así que
    pueden ser objetos de LangChain (`HumanMessage.type == "human"`) o dicts con
    `role`. Si no se identifica ninguno, cae al último de la lista.
    """
    for mensaje in reversed(mensajes):
        if isinstance(mensaje, dict):
            rol = mensaje.get("role")
        else:
            rol = getattr(mensaje, "type", None)
        if rol in ("human", "user"):
            return _texto_mensaje(mensaje)
    return _texto_mensaje(mensajes[-1]) if mensajes else ""


def _valor_enum(valor: Enum | None) -> str | None:
    """Serializa un enum del contrato a su forma canónica corta (`"Principiante"`)."""
    return valor.value if isinstance(valor, Enum) else valor


def construir_nodo_supervisor(generador: GeneradorEstructurado) -> NodoSupervisor:
    """Devuelve el nodo que clasifica la intención y escribe las 5 claves al estado."""

    async def nodo_supervisor(state: AgentState) -> dict:
        mensaje = _ultimo_mensaje_usuario(state.get("mensajes") or [])
        intencion = await clasificar_intencion(
            mensaje,
            state.get("tema_pedido_chat"),
            generador,
        )
        return {
            "tema_consulta": intencion.tema_consulta,
            "perfil_destinatario": _valor_enum(intencion.perfil_destinatario),
            "formato_salida": _valor_enum(intencion.formato_salida),
            "nicho_sector": _valor_enum(intencion.nicho_sector),
            "nivel_detalle": _valor_enum(intencion.nivel_detalle),
        }

    return nodo_supervisor
