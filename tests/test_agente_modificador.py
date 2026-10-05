"""Tests del núcleo del Modificador (sin LangGraph, con dobles)."""

from __future__ import annotations

import asyncio

import pytest

from test_agente_redactor_pedagogico import (
    CHUNKS,
    SPEC,
    FakeGenerator,
    salida_valida,
    solicitud,
)
from src.agentes.agente_modificador import modificar_contenido
from src.agentes.agente_redactor_pedagogico import EstadoRedactor
from src.contracts import FormatoSalida, SolicitudAdaptacion
from src.errores import ErrorFormatoNoDisponible, ErrorLLM, ErrorSalidaInvalida

INSTRUCCION = "Acorta la introducción y no toques los demás items."


def contenido_previo() -> dict:
    return salida_valida("Flashcards")["contenido"]


def ejecutar(salida=None, formato="Flashcards", instruccion=INSTRUCCION, contenido=None):
    generador = FakeGenerator(salida if salida is not None else salida_valida(formato))
    resultado = asyncio.run(
        modificar_contenido(
            solicitud=solicitud(formato),
            chunks=CHUNKS,
            contenido_actual=contenido if contenido is not None else contenido_previo(),
            instruccion_modificacion=instruccion,
            especificacion_pedagogica=SPEC,
            generador=generador,
        )
    )
    return resultado, generador


def test_modificacion_valida_devuelve_contenido_tipado():
    resultado, generador = ejecutar()

    assert resultado.estado is EstadoRedactor.GENERACION_CON_EVIDENCIA
    assert resultado.contenido is not None
    assert resultado.contenido.items[0].anclaje == ["chunk-1"]
    assert generador.output_model.__name__ == "RespuestaGenerador"


def test_prompt_incluye_contenido_actual_e_instruccion():
    resultado, generador = ejecutar()

    assert "## CURRENT APPROVED CONTENT" in generador.prompt
    assert "## UNTRUSTED MODIFICATION REQUEST" in generador.prompt
    assert "Redes privadas en la nube" in generador.prompt  # título del contenido previo
    assert INSTRUCCION in generador.prompt
    assert "## TASK OVERRIDE" in generador.prompt


@pytest.mark.parametrize("instruccion", ["", "   "])
def test_instruccion_vacia_se_rechaza(instruccion):
    with pytest.raises(ErrorSalidaInvalida):
        ejecutar(instruccion=instruccion)


def test_sin_chunks_abstiene_sin_llamar_al_generador():
    generador = FakeGenerator(salida_valida("Flashcards"))
    resultado = asyncio.run(
        modificar_contenido(
            solicitud=solicitud("Flashcards"),
            chunks=[],
            contenido_actual=contenido_previo(),
            instruccion_modificacion=INSTRUCCION,
            especificacion_pedagogica=SPEC,
            generador=generador,
        )
    )

    assert resultado.estado is EstadoRedactor.EVIDENCIA_INSUFICIENTE
    assert resultado.contenido is None
    assert generador.output_model is None


def test_anchor_ajeno_se_rechaza_antes_de_propagarse():
    salida = salida_valida("Flashcards")
    salida["contenido"]["items"][0]["anclaje"] = ["chunk-ajeno"]

    with pytest.raises(ErrorSalidaInvalida):
        ejecutar(salida=salida)


def test_contenido_previo_sin_items_se_rechaza():
    with pytest.raises(ErrorSalidaInvalida):
        ejecutar(contenido={"titulo": "Sin items"})


def test_guion_de_clase_rechazado_en_esta_fase():
    solicitud_guion = SolicitudAdaptacion.model_construct(
        **{
            "documento_titulo": "Guía",
            "documento_contenido": "Contenido",
            "perfil_destinatario": "Principiante",
            "formato_salida": FormatoSalida.GUION_CLASE,
            "nicho_sector": "General",
            "nivel_detalle": "Didactico",
        }
    )
    with pytest.raises(ErrorFormatoNoDisponible):
        asyncio.run(
            modificar_contenido(
                solicitud=solicitud_guion,
                chunks=CHUNKS,
                contenido_actual=contenido_previo(),
                instruccion_modificacion=INSTRUCCION,
                especificacion_pedagogica=SPEC,
                generador=FakeGenerator({}),
            )
        )


def test_error_del_generador_se_convierte_en_error_llm():
    with pytest.raises(ErrorLLM):
        ejecutar(salida=ErrorLLM("Fallo del proveedor"))
