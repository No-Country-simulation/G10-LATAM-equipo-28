"""Pruebas del adaptador `GeneradorLangchain` (modelo LangChain inyectado).

Ejecutar:   pytest tests/test_generador_langchain.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agentes.generador_langchain import GeneradorLangchain  # noqa: E402
from src.errores import ErrorLLM  # noqa: E402


class SalidaEjemplo(BaseModel):
    tema_consulta: str


class FakeEstructurado:
    """Doble del runnable que devuelve `with_structured_output`."""

    def __init__(self, salida: Any, error: Exception | None = None):
        self.salida = salida
        self.error = error
        self.entrada: Any = None

    async def ainvoke(self, entrada: Any) -> Any:
        self.entrada = entrada
        if self.error is not None:
            raise self.error
        return self.salida


class FakeModelo:
    """Doble de un chat model de LangChain."""

    def __init__(self, salida: Any, error: Exception | None = None):
        self.salida = salida
        self.error = error
        self.schema: type[BaseModel] | None = None
        self.kwargs: dict[str, Any] = {}
        self.runnable = FakeEstructurado(salida, error)

    def with_structured_output(
        self, schema: type[BaseModel], **kwargs: Any
    ) -> FakeEstructurado:
        self.schema = schema
        self.kwargs = kwargs
        return self.runnable


# =============================================================================
# Camino feliz
# =============================================================================


def test_generate_devuelve_la_salida_estructurada():
    modelo = FakeModelo({"tema_consulta": "VCN"})

    resultado = asyncio.run(
        GeneradorLangchain(modelo).generate(prompt="hola", output_model=SalidaEjemplo)
    )

    assert resultado == {"tema_consulta": "VCN"}


def test_pasa_el_output_model_a_with_structured_output():
    modelo = FakeModelo({"tema_consulta": "VCN"})

    asyncio.run(
        GeneradorLangchain(modelo).generate(prompt="hola", output_model=SalidaEjemplo)
    )

    assert modelo.schema is SalidaEjemplo


def test_envia_el_prompt_al_modelo():
    modelo = FakeModelo({"tema_consulta": "VCN"})

    asyncio.run(
        GeneradorLangchain(modelo).generate(prompt="explica VCN", output_model=SalidaEjemplo)
    )

    assert modelo.runnable.entrada == "explica VCN"


def test_devuelve_instancia_si_el_modelo_la_entrega():
    instancia = SalidaEjemplo(tema_consulta="VCN")
    modelo = FakeModelo(instancia)

    resultado = asyncio.run(
        GeneradorLangchain(modelo).generate(prompt="hola", output_model=SalidaEjemplo)
    )

    assert resultado is instancia


# =============================================================================
# Errores
# =============================================================================


def test_error_del_modelo_se_convierte_en_error_llm():
    modelo = FakeModelo(None, error=RuntimeError("offline"))

    with pytest.raises(ErrorLLM):
        asyncio.run(
            GeneradorLangchain(modelo).generate(prompt="hola", output_model=SalidaEjemplo)
        )


def test_error_llm_del_modelo_se_propaga_sin_reenvolver():
    original = ErrorLLM("fallo original")
    modelo = FakeModelo(None, error=original)

    with pytest.raises(ErrorLLM) as excinfo:
        asyncio.run(
            GeneradorLangchain(modelo).generate(prompt="hola", output_model=SalidaEjemplo)
        )

    assert excinfo.value is original


# =============================================================================
# Parámetro `method` (quirks de proveedor)
# =============================================================================


def test_sin_method_no_se_pasa_el_argumento():
    """Con method=None NO se pasa el kwarg: el backend rechaza None explícito."""
    modelo = FakeModelo({"tema_consulta": "VCN"})

    asyncio.run(
        GeneradorLangchain(modelo).generate(prompt="hola", output_model=SalidaEjemplo)
    )

    assert modelo.kwargs == {}


def test_method_explicito_se_propaga_a_with_structured_output():
    modelo = FakeModelo({"tema_consulta": "VCN"})

    asyncio.run(
        GeneradorLangchain(modelo, method="function_calling").generate(
            prompt="hola", output_model=SalidaEjemplo
        )
    )

    assert modelo.kwargs == {"method": "function_calling"}
