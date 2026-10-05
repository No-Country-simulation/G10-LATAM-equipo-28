"""Tests del adaptador de nodo del Crítico/Revisor (estado -> estado)."""

from __future__ import annotations

import asyncio

from test_agente_redactor_pedagogico import FakeGenerator, salida_valida
from src.agentes.critico_revisor import construir_nodo_critico_revisor
from src.errores import CodigoError, ErrorLLM, MENSAJE_POR_DEFECTO


def contenido_valido() -> dict:
    return salida_valida("Flashcards")["contenido"]


def revision(**cambios) -> dict:
    base = {"aprobado": True, "claridad_pedagogica": "Alta", "observaciones": "Todo correcto."}
    return {**base, **cambios}


def state_base() -> dict:
    return {
        "contenido_adaptado": contenido_valido(),
        "formato_salida": "Flashcards",
        "chunks_fuente_estructurados": [
            {"id": "chunk-1", "texto": "Una VCN es una red privada.", "score": 0.9}
        ],
        "aprobado": None,
        "evaluacion_calidad": None,
    }


def ejecutar(state, salida=None, calculador=None):
    generador = FakeGenerator(salida if salida is not None else revision())
    nodo = construir_nodo_critico_revisor(generador, calculador_fidelidad=calculador)
    return asyncio.run(nodo(state)), generador


def test_nodo_escribe_aprobado_y_evaluacion():
    resultado, generador = ejecutar(state_base(), revision(aprobado=False, claridad_pedagogica="Baja"))

    assert resultado == {
        "aprobado": False,
        "evaluacion_calidad": {"claridad_pedagogica": "Baja", "observaciones": "Todo correcto."},
    }
    assert generador.prompt and "chunk-1" in generador.prompt


def test_nodo_sin_contenido_no_llama_al_generador():
    resultado, generador = ejecutar({**state_base(), "contenido_adaptado": None})

    assert resultado["aprobado"] is False
    assert "No hay contenido" in resultado["evaluacion_calidad"]["observaciones"]
    assert not generador.prompt


def test_nodo_con_formato_invalido_no_llama_al_generador():
    resultado, generador = ejecutar({**state_base(), "formato_salida": "Formato Inexistente"})

    assert resultado["aprobado"] is False
    assert not generador.prompt


def test_nodo_prefiere_el_canal_estructurado_sobre_el_legacy():
    state = {
        **state_base(),
        "chunks_fuente_estructurados": [{"id": "chunk-1", "texto": "Fuente nueva.", "score": 0.9}],
        "chunks_fuente_confirmados": [{"id": "legacy-1", "texto": "Fuente vieja."}],
    }
    _, generador = ejecutar(state)

    assert "chunk-1" in generador.prompt
    assert "legacy-1" not in generador.prompt


def test_nodo_error_del_llm_devuelve_fallo_sin_excepcion():
    resultado, _ = ejecutar(state_base(), ErrorLLM("Detalle privado"))

    assert resultado["aprobado"] is False
    assert resultado["evaluacion_calidad"]["observaciones"] == MENSAJE_POR_DEFECTO[CodigoError.FALLO_LLM]
    assert "Detalle privado" not in resultado["evaluacion_calidad"]["observaciones"]


def test_nodo_pasa_el_calculador_inyectado():
    class Calculador:
        def calcular(self, *, contenido, chunks):
            return {"anclaje_fuente_score": 0.95, "supero_umbral": True}

    resultado, _ = ejecutar(state_base(), calculador=Calculador())

    assert resultado["evaluacion_calidad"]["anclaje_fuente_score"] == 0.95
