"""Pruebas del agente Investigador (recuperador y generador inyectados).

Ejecutar:   pytest tests/test_agente_investigador.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agentes.agente_investigador import (  # noqa: E402
    UMBRAL_COBERTURA,
    ChunkConScore,
    MensajeAclaracion,
    ResultadoInvestigador,
    investigar,
)
from src.errores import ErrorLLM, ErrorSalidaInvalida  # noqa: E402
from src.prompts.investigador import construir_prompt_investigador  # noqa: E402


class FakeGenerator:
    def __init__(self, salida: Any):
        self.salida = salida
        self.prompt = ""
        self.output_model: type[BaseModel] | None = None

    async def generate(self, *, prompt: str, output_model: type[BaseModel]) -> Any:
        self.prompt = prompt
        self.output_model = output_model
        if isinstance(self.salida, Exception):
            raise self.salida
        return self.salida


class FakeRecuperador:
    def __init__(self, chunks: list[Any]):
        self.chunks = chunks
        self.consulta: str | None = None
        self.top_k: int | None = None

    def buscar(self, consulta: str, top_k: int = 5) -> list[Any]:
        self.consulta = consulta
        self.top_k = top_k
        return self.chunks


TITULO = "Manual de redes en la nube"
CHUNK_MATCH = {"id": "chunk-1", "texto": "Una VCN es una red privada.", "score": 0.91}
CHUNK_BAJO = {"id": "chunk-2", "texto": "Texto poco relacionado.", "score": 0.40}


# =============================================================================
# Cobertura
# =============================================================================


def test_chunk_sobre_umbral_confirma_fuente_sin_llamar_al_llm():
    recuperador = FakeRecuperador([CHUNK_MATCH, CHUNK_BAJO])
    generador = FakeGenerator({"mensaje": "no debería usarse"})

    resultado = asyncio.run(
        investigar("VCN", recuperador, generador, TITULO)
    )

    assert resultado.fuente_confirmada is True
    assert [c.id for c in resultado.chunks_fuente_confirmados] == ["chunk-1"]
    assert resultado.mensaje_aclaracion is None
    assert generador.output_model is None


def test_score_exactamente_en_el_umbral_confirma():
    en_umbral = {"id": "c", "texto": "justo en el umbral", "score": UMBRAL_COBERTURA}
    recuperador = FakeRecuperador([en_umbral])
    generador = FakeGenerator({})

    resultado = asyncio.run(investigar("VCN", recuperador, generador, TITULO))

    assert resultado.fuente_confirmada is True


def test_sin_match_redacta_mensaje_de_aclaracion():
    recuperador = FakeRecuperador([CHUNK_BAJO])
    generador = FakeGenerator({"mensaje": "El documento trata sobre redes, ¿querés seguir?"})

    resultado = asyncio.run(investigar("Kubernetes", recuperador, generador, TITULO))

    assert resultado.fuente_confirmada is False
    assert resultado.mensaje_aclaracion == "El documento trata sobre redes, ¿querés seguir?"
    assert resultado.chunks_fuente_confirmados == []
    assert generador.output_model is MensajeAclaracion
    assert TITULO in generador.prompt


def test_sin_chunks_tambien_redacta_mensaje():
    recuperador = FakeRecuperador([])
    generador = FakeGenerator({"mensaje": "No hay coincidencias."})

    resultado = asyncio.run(investigar("Kubernetes", recuperador, generador, TITULO))

    assert resultado.fuente_confirmada is False
    assert resultado.mensaje_aclaracion == "No hay coincidencias."


# =============================================================================
# Errores y validación
# =============================================================================


def test_tema_vacio_se_rechaza_sin_consultar_el_recuperador():
    recuperador = FakeRecuperador([CHUNK_MATCH])
    generador = FakeGenerator({})

    with pytest.raises(ErrorSalidaInvalida):
        asyncio.run(investigar("   ", recuperador, generador, TITULO))

    assert recuperador.consulta is None


def test_fallo_del_generador_en_aclaracion_se_convierte_en_error_llm():
    recuperador = FakeRecuperador([CHUNK_BAJO])

    with pytest.raises(ErrorLLM):
        asyncio.run(
            investigar("Kubernetes", recuperador, FakeGenerator(RuntimeError("offline")), TITULO)
        )


def test_mensaje_de_aclaracion_vacio_se_rechaza():
    recuperador = FakeRecuperador([CHUNK_BAJO])
    generador = FakeGenerator({"mensaje": "   "})

    with pytest.raises(ErrorSalidaInvalida):
        asyncio.run(investigar("Kubernetes", recuperador, generador, TITULO))


def test_chunk_recuperado_invalido_se_rechaza():
    recuperador = FakeRecuperador([{"id": "c", "texto": "x", "score": 2.0}])
    generador = FakeGenerator({})

    with pytest.raises(ErrorSalidaInvalida):
        asyncio.run(investigar("VCN", recuperador, generador, TITULO))


def test_resultado_confirmado_sin_chunks_es_incoherente():
    with pytest.raises(ValidationError):
        ResultadoInvestigador(fuente_confirmada=True)


def test_resultado_no_confirmado_sin_mensaje_es_incoherente():
    with pytest.raises(ValidationError):
        ResultadoInvestigador(fuente_confirmada=False)


def test_chunk_con_score_fuera_de_rango_no_valida():
    with pytest.raises(ValidationError):
        ChunkConScore(id="c", texto="x", score=1.5)


# =============================================================================
# Prompt
# =============================================================================


def test_prompt_incluye_titulo_y_resumen():
    prompt = construir_prompt_investigador("Kubernetes", TITULO, "Redes privadas y subredes.")

    assert TITULO in prompt
    assert "Redes privadas y subredes." in prompt
    assert "Kubernetes" in prompt
    assert "## SYSTEM POLICY" in prompt
    assert "no invent" in prompt.lower()
