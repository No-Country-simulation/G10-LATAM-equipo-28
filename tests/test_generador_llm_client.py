from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel

from src.agentes.generador_llm_client import GeneradorLLMClient


class SalidaPrueba(BaseModel):
    texto: str


class FakeRunnable:
    def __init__(self, resultado: Any):
        self.resultado = resultado
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return self.resultado


class FakeLLM:
    def __init__(self, runnable: FakeRunnable):
        self.runnable = runnable
        self.output_model = None

    def with_structured_output(self, output_model):
        self.output_model = output_model
        return self.runnable


def test_adapter_usa_get_llm_y_salida_estructurada_de_la_api_compartida():
    rate_limiter = object()
    respuesta = SalidaPrueba(texto="salida tipada")
    runnable = FakeRunnable(respuesta)
    llm = FakeLLM(runnable)
    factory_calls = []

    def get_llm(*, mensajes, rate_limiter):
        factory_calls.append((mensajes, rate_limiter))
        return llm

    generator = GeneradorLLMClient(get_llm, rate_limiter)
    salida = asyncio.run(
        generator.generate(prompt="instrucciones", output_model=SalidaPrueba)
    )

    assert salida == {"texto": "salida tipada"}
    assert factory_calls == [([{"role": "user", "content": "instrucciones"}], rate_limiter)]
    assert llm.output_model is SalidaPrueba
    assert runnable.messages == [{"role": "user", "content": "instrucciones"}]


def test_adapter_preserva_respuesta_dict_de_langchain():
    respuesta = {"texto": "salida dict"}
    runnable = FakeRunnable(respuesta)
    llm = FakeLLM(runnable)
    generator = GeneradorLLMClient(lambda **_: llm, rate_limiter=object())

    salida = asyncio.run(generator.generate(prompt="p", output_model=SalidaPrueba))

    assert salida is respuesta
