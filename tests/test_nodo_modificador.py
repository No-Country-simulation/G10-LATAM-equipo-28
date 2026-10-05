"""Tests del adaptador de nodo del Modificador (estado -> estado)."""

from __future__ import annotations

import asyncio

from test_agente_redactor_pedagogico import SPEC, FakeGenerator, salida_valida
from src.agentes.critico_revisor import construir_nodo_critico_revisor
from src.agentes.modificador import construir_nodo_modificador
from src.agentes.redactor import obtener_solicitud_redactor

INSTRUCCION = "Acorta la introducción y no toques los demás items."


def contenido_previo() -> dict:
    return salida_valida("Flashcards")["contenido"]


def state_base() -> dict:
    return {
        "contenido_adaptado": contenido_previo(),
        "formato_salida": "Flashcards",
        "chunks_fuente_estructurados": [
            {"id": "chunk-1", "texto": "Una VCN es una red privada.", "score": 0.9}
        ],
        "instruccion_modificacion": INSTRUCCION,
        "vueltas_modificacion": 1,
        "documento_titulo": "Guía de redes",
        "documento_contenido": "Una VCN es una red privada y personalizable en la nube.",
        "perfil_destinatario": "Principiante",
        "nicho_sector": "General",
        "nivel_detalle": "Didactico",
    }


def construir(salida=None):
    return construir_nodo_modificador(
        FakeGenerator(salida if salida is not None else salida_valida("Flashcards")),
        lambda *_: SPEC,
        obtener_solicitud_redactor,
    )


def test_nodo_incrementa_vueltas_y_escribe_contenido():
    resultado = asyncio.run(construir()(state_base()))

    assert resultado["vueltas_modificacion"] == 2
    assert resultado["contenido_adaptado"]["items"][0]["anclaje"] == ["chunk-1"]
    assert resultado["aprobado"] is None
    assert resultado["evaluacion_calidad"] is None
    assert resultado["error"] is None


def test_nodo_sin_instruccion_no_llama_y_conserva_contenido():
    state = {**state_base(), "instruccion_modificacion": "   "}
    generador = FakeGenerator(salida_valida("Flashcards"))
    nodo = construir_nodo_modificador(generador, lambda *_: SPEC, obtener_solicitud_redactor)

    resultado = asyncio.run(nodo(state))

    assert resultado["vueltas_modificacion"] == 2
    assert resultado["error"]
    assert "contenido_adaptado" not in resultado  # no borra lo aprobado
    assert not generador.prompt


def test_nodo_sin_contenido_aprobado_reporta_error():
    resultado = asyncio.run(construir()({**state_base(), "contenido_adaptado": None}))

    assert resultado["vueltas_modificacion"] == 2
    assert "No hay contenido" in resultado["error"]


def test_nodo_falla_y_no_borra_el_contenido_aprobado():
    resultado = asyncio.run(construir(salida=RuntimeError("offline"))(state_base()))

    assert resultado["vueltas_modificacion"] == 2
    assert resultado["error"]
    assert "contenido_adaptado" not in resultado


def test_nodo_ignora_el_canal_legacy_si_el_estructurado_esta_presente():
    state = {
        **state_base(),
        "chunks_fuente_estructurados": [{"id": "chunk-1", "texto": "Nueva.", "score": 0.9}],
        "chunks_fuente_confirmados": [{"id": "legacy-1", "texto": "Vieja."}],
    }
    generador = FakeGenerator(salida_valida("Flashcards"))
    nodo = construir_nodo_modificador(generador, lambda *_: SPEC, obtener_solicitud_redactor)

    asyncio.run(nodo(state))

    assert "chunk-1" in generador.prompt
    assert "legacy-1" not in generador.prompt


def test_composicion_langgraph_modificador_y_revisor():
    from langgraph.graph import END, START, StateGraph

    from src.agent_state import AgentState

    builder = StateGraph(AgentState)
    builder.add_node("modificador", construir())
    builder.add_node(
        "critico_revisor",
        construir_nodo_critico_revisor(
            FakeGenerator(
                {"aprobado": True, "claridad_pedagogica": "Alta", "observaciones": "Ok."}
            )
        ),
    )
    builder.add_edge(START, "modificador")
    builder.add_edge("modificador", "critico_revisor")
    builder.add_edge("critico_revisor", END)

    resultado = asyncio.run(builder.compile().ainvoke(state_base()))

    assert resultado["vueltas_modificacion"] == 2
    assert resultado["aprobado"] is True
    assert resultado["evaluacion_calidad"]["claridad_pedagogica"] == "Alta"
