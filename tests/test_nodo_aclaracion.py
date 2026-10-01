"""Pruebas del interrupt HITL de aclaración (1 ronda).

Ejecutar:   pytest tests/test_nodo_aclaracion.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent_state import AgentState  # noqa: E402
from src.grafo import nodo_aclaracion  # noqa: E402


def _grafo_efimero():
    builder = StateGraph(AgentState)
    builder.add_node("aclaracion", nodo_aclaracion)
    builder.set_entry_point("aclaracion")
    builder.add_edge("aclaracion", END)
    return builder


async def _correr(resume: dict | None = None):
    conexion = await aiosqlite.connect(":memory:")
    try:
        grafo = _grafo_efimero().compile(checkpointer=AsyncSqliteSaver(conexion))
        config = {"configurable": {"thread_id": "aclaracion-test"}}
        salida = await grafo.ainvoke({"mensaje_aclaracion": "El documento trata de VCN."}, config)
        if resume is not None:
            salida = await grafo.ainvoke(Command(resume=resume), config)
        return salida
    finally:
        await conexion.close()


def test_pausa_y_expone_el_mensaje_de_aclaracion():
    salida = asyncio.run(_correr())

    assert salida["__interrupt__"]
    aviso = salida["__interrupt__"][0].value
    assert aviso["tipo"] == "aclaracion"
    assert aviso["mensaje_aclaracion"] == "El documento trata de VCN."


def test_al_reanudar_guarda_la_respuesta():
    salida = asyncio.run(_correr(resume={"respuesta": "seguir con VCN"}))

    assert salida["respuesta_aclaracion_usuario"] == "seguir con VCN"


def test_reanudar_sin_respuesta_guarda_none():
    salida = asyncio.run(_correr(resume={}))

    # LangGraph no crea la clave cuando el nodo escribe None; queda ausente o None.
    assert salida.get("respuesta_aclaracion_usuario") is None
