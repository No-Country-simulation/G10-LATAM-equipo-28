"""Pruebas del nodo LangGraph del Investigador (recuperador y generador inyectados).

Ejecutar:   pytest tests/test_nodo_investigador.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agentes.investigador import construir_nodo_investigador  # noqa: E402


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

    def buscar(self, consulta: str, top_k: int = 5) -> list[Any]:
        self.consulta = consulta
        return self.chunks


TITULO = "Manual de redes en la nube"
CHUNK_MATCH = {"id": "chunk-1", "texto": "Una VCN es una red privada.", "score": 0.91}
CHUNK_BAJO = {"id": "chunk-2", "texto": "Texto poco relacionado.", "score": 0.40}


def _state(**extra: Any) -> dict:
    base = {"tema_consulta": "VCN", "documento_titulo": TITULO}
    base.update(extra)
    return base


# =============================================================================
# Cobertura
# =============================================================================


def test_con_cobertura_escribe_las_cuatro_claves_y_no_llama_al_llm():
    recuperador = FakeRecuperador([CHUNK_MATCH, CHUNK_BAJO])
    generador = FakeGenerator({"mensaje": "no debería usarse"})

    nodo = construir_nodo_investigador(recuperador, generador)
    salida = asyncio.run(nodo(_state()))

    assert salida["fuente_confirmada"] is True
    assert salida["chunks_fuente_confirmados"] == ["chunk-1"]
    assert salida["chunks_fuente_estructurados"] == [CHUNK_MATCH]
    assert salida["mensaje_aclaracion"] is None
    assert generador.output_model is None  # el LLM no se usó


def test_usa_tema_pedido_chat_como_fallback():
    recuperador = FakeRecuperador([CHUNK_MATCH])
    nodo = construir_nodo_investigador(recuperador, FakeGenerator({}))

    salida = asyncio.run(nodo({"tema_pedido_chat": "redes VCN", "documento_titulo": TITULO}))

    assert recuperador.consulta == "redes VCN"
    assert salida["fuente_confirmada"] is True


# =============================================================================
# Sin cobertura
# =============================================================================


def test_sin_cobertura_escribe_aclaracion_y_limpia_canal_estructurado():
    recuperador = FakeRecuperador([CHUNK_BAJO])
    generador = FakeGenerator({"mensaje": "El documento trata sobre redes, ¿seguimos?"})

    nodo = construir_nodo_investigador(recuperador, generador)
    salida = asyncio.run(nodo(_state()))

    assert salida["fuente_confirmada"] is False
    assert salida["chunks_fuente_confirmados"] == []
    assert salida["chunks_fuente_estructurados"] == []
    assert salida["mensaje_aclaracion"] == "El documento trata sobre redes, ¿seguimos?"
    assert "error" not in salida


# =============================================================================
# Errores
# =============================================================================


def test_tema_vacio_devuelve_error_sin_explotar():
    recuperador = FakeRecuperador([CHUNK_MATCH])
    nodo = construir_nodo_investigador(recuperador, FakeGenerator({}))

    salida = asyncio.run(nodo({"documento_titulo": TITULO}))

    assert salida["fuente_confirmada"] is False
    assert salida["status"] == "error" and salida["error"]
    assert recuperador.consulta is None  # no consulta el vector store


def test_fallo_del_generador_se_reporta_como_error():
    recuperador = FakeRecuperador([CHUNK_BAJO])
    generador = FakeGenerator(RuntimeError("offline"))

    nodo = construir_nodo_investigador(recuperador, generador)
    salida = asyncio.run(nodo(_state()))

    assert salida["fuente_confirmada"] is False
    assert salida["status"] == "error" and salida["error"]
    assert salida["chunks_fuente_estructurados"] == []
