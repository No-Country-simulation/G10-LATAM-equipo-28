"""Tests del núcleo del Crítico/Revisor (sin LangGraph, con dobles)."""

from __future__ import annotations

import asyncio

import pytest

from test_agente_redactor_pedagogico import CHUNKS, FakeGenerator, salida_valida
from src.agentes.agente_critico_revisor import ResultadoRevision, revisar_contenido
from src.contracts import ClaridadPedagogica, FormatoSalida
from src.errores import ErrorLLM, ErrorSalidaInvalida

FORMATO = FormatoSalida.FLASHCARDS


def contenido_valido() -> dict:
    return salida_valida("Flashcards")["contenido"]


def revision(**cambios) -> dict:
    base = {"aprobado": True, "claridad_pedagogica": "Alta", "observaciones": "Todo correcto."}
    return {**base, **cambios}


class FakeCalculador:
    def __init__(self, score: dict):
        self.score = score
        self.llamadas = 0

    def calcular(self, *, contenido, chunks):
        self.llamadas += 1
        return self.score


def ejecutar(salida, calculador=None, formato=FORMATO, contenido=None, chunks=CHUNKS):
    generador = salida if isinstance(salida, FakeGenerator) else FakeGenerator(salida)
    resultado = asyncio.run(
        revisar_contenido(
            contenido=contenido if contenido is not None else contenido_valido(),
            formato_salida=formato,
            chunks=chunks,
            generador=generador,
            calculador_fidelidad=calculador,
        )
    )
    return resultado, generador


def test_aprobado_escribe_claridad_y_observaciones():
    resultado, generador = ejecutar(revision(aprobado=True, claridad_pedagogica="Alta"))

    assert isinstance(resultado, ResultadoRevision)
    assert resultado.aprobado is True
    assert resultado.evaluacion_calidad["claridad_pedagogica"] == "Alta"
    assert resultado.evaluacion_calidad["observaciones"] == "Todo correcto."
    assert generador.output_model.__name__ == "RevisionOut"


def test_rechazo_conserva_observaciones_accionables():
    resultado, _ = ejecutar(
        revision(aprobado=False, claridad_pedagogica="Media",
                 observaciones="El item 2 inventa una cifra; corregir el titulo.")
    )

    assert resultado.aprobado is False
    assert "inventa una cifra" in resultado.evaluacion_calidad["observaciones"]


@pytest.mark.parametrize("vacio", ["", "   "])
def test_observaciones_vacias_se_normalizan(vacio):
    resultado, _ = ejecutar(revision(observaciones=vacio))

    assert resultado.evaluacion_calidad["observaciones"] == "Sin observaciones."


def test_sin_calculador_no_inventa_score_de_fidelidad():
    resultado, _ = ejecutar(revision())

    assert "anclaje_fuente_score" not in resultado.evaluacion_calidad
    assert set(resultado.evaluacion_calidad) == {"claridad_pedagogica", "observaciones"}


def test_calculador_inyectado_agrega_metricas_de_fidelidad():
    calculador = FakeCalculador({
        "anclaje_fuente_score": 0.9,
        "afirmaciones_evaluadas": 4,
        "afirmaciones_soportadas": 4,
        "supero_umbral": True,
    })
    resultado, _ = ejecutar(revision(), calculador=calculador)

    assert calculador.llamadas == 1
    assert resultado.evaluacion_calidad["anclaje_fuente_score"] == 0.9
    assert resultado.evaluacion_calidad["afirmaciones_evaluadas"] == 4
    assert resultado.evaluacion_calidad["claridad_pedagogica"] == "Alta"


def test_fidelidad_bajo_umbral_fuerza_requiere_revision():
    calculador = FakeCalculador({"anclaje_fuente_score": 0.4, "supero_umbral": False})
    resultado, _ = ejecutar(revision(claridad_pedagogica="Alta"), calculador=calculador)

    assert (
        resultado.evaluacion_calidad["claridad_pedagogica"]
        == ClaridadPedagogica.REQUIERE_REVISION.value
    )


def test_error_del_generador_se_convierte_en_error_llm():
    with pytest.raises(ErrorLLM):
        ejecutar(FakeGenerator(ErrorLLM("Fallo del proveedor")))


@pytest.mark.parametrize(
    "salida",
    [
        {"aprobado": "quizas", "claridad_pedagogica": "Alta", "observaciones": "x"},
        {"aprobado": True, "claridad_pedagogica": "Altisima", "observaciones": "x"},
        {"aprobado": True, "claridad_pedagogica": "Alta", "observaciones": "x", "campo_extra": 1},
    ],
    ids=["aprobado-no-booleano", "claridad-invalida", "campo-extra"],
)
def test_salida_invalida_se_rechaza(salida):
    with pytest.raises(ErrorSalidaInvalida):
        ejecutar(salida)


@pytest.mark.parametrize("contenido", [{}, {"items": []}, "texto suelto"])
def test_contenido_vacio_o_sin_items_se_rechaza(contenido):
    with pytest.raises(ErrorSalidaInvalida):
        ejecutar(revision(), contenido=contenido)


def test_chunks_invalidos_se_rechazan():
    with pytest.raises(ErrorSalidaInvalida):
        ejecutar(revision(), chunks=[{"texto": "sin id"}])


def test_formato_invalido_se_rechaza():
    with pytest.raises(ErrorSalidaInvalida):
        ejecutar(revision(), formato="Flashcards")


def test_prompt_separa_politica_y_datos_con_schema_y_chunks():
    resultado, generador = ejecutar(revision())

    prompt = generador.prompt
    assert "## SYSTEM POLICY" in prompt
    assert "## UNTRUSTED GENERATED CONTENT" in prompt
    assert "## UNTRUSTED SOURCE CONTEXT" in prompt
    assert prompt.index("## SYSTEM POLICY") < prompt.index("## UNTRUSTED SOURCE CONTEXT")
    assert all(chunk["id"] in prompt for chunk in CHUNKS)
    assert "frente" in prompt  # el sub-esquema del formato va incluido
    assert "no reescribas" in prompt.lower()
