"""Pruebas del nodo LangGraph del Supervisor (adaptador, generador inyectado).

Ejecutar:   pytest tests/test_nodo_supervisor.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agentes.supervisor import construir_nodo_supervisor  # noqa: E402


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


# =============================================================================
# Nodo: claves y normalización
# =============================================================================


def test_nodo_escribe_las_cinco_claves_del_state():
    generador = FakeGenerator(
        {
            "tema_consulta": "VCN",
            "perfil_destinatario": "Principiante",
            "formato_salida": "Flashcards",
            "nicho_sector": "General",
            "nivel_detalle": "Didactico",
        }
    )
    nodo = construir_nodo_supervisor(generador)

    salida = asyncio.run(
        nodo({"mensajes": [{"role": "user", "content": "Quiero flashcards de VCN"}]})
    )

    assert set(salida) == {
        "tema_consulta",
        "perfil_destinatario",
        "formato_salida",
        "nicho_sector",
        "nivel_detalle",
    }
    assert salida["tema_consulta"] == "VCN"
    # Forma canónica corta, no la larga.
    assert salida["perfil_destinatario"] == "Principiante"
    assert salida["formato_salida"] == "Flashcards"


def test_nodo_normaliza_alias_largos_a_forma_corta():
    generador = FakeGenerator(
        {
            "tema_consulta": "Scrum",
            "perfil_destinatario": "Líder Técnico / Arquitecto",
            "formato_salida": "Quiz Interactivo con Justificaciones",
            "nicho_sector": "E-commerce",
            "nivel_detalle": "Estándar",
        }
    )
    nodo = construir_nodo_supervisor(generador)

    salida = asyncio.run(nodo({"mensajes": [HumanMessage(content="Scrum")]}))

    assert salida["perfil_destinatario"] == "Lider Tecnico"
    assert salida["formato_salida"] == "Quiz"
    assert salida["nicho_sector"] == "E-commerce"
    assert salida["nivel_detalle"] == "Estandar"


def test_parametros_ausentes_quedan_en_none():
    generador = FakeGenerator({"tema_consulta": "VCN"})
    nodo = construir_nodo_supervisor(generador)

    salida = asyncio.run(nodo({"mensajes": [HumanMessage(content="VCN")]}))

    assert salida["perfil_destinatario"] is None
    assert salida["formato_salida"] is None
    assert salida["nicho_sector"] is None
    assert salida["nivel_detalle"] is None


# =============================================================================
# Extracción del mensaje del usuario
# =============================================================================


def test_usa_el_ultimo_mensaje_humano_e_ignora_la_respuesta_del_modelo():
    generador = FakeGenerator({"tema_consulta": "VCN"})
    nodo = construir_nodo_supervisor(generador)

    asyncio.run(
        nodo(
            {
                "mensajes": [
                    HumanMessage(content="primero"),
                    AIMessage(content="respuesta del sistema"),
                    HumanMessage(content="segundo"),
                ]
            }
        )
    )

    assert "segundo" in generador.prompt
    assert "primero" not in generador.prompt


def test_fallback_usa_tema_pedido_chat_si_el_modelo_no_extrae_tema():
    generador = FakeGenerator({"tema_consulta": None})
    nodo = construir_nodo_supervisor(generador)

    salida = asyncio.run(
        nodo(
            {
                "mensajes": [HumanMessage(content="hola")],
                "tema_pedido_chat": "redes VCN",
            }
        )
    )

    assert salida["tema_consulta"] == "redes VCN"


def test_mensajes_vacios_no_revientan():
    generador = FakeGenerator({"tema_consulta": None})
    nodo = construir_nodo_supervisor(generador)

    salida = asyncio.run(nodo({"mensajes": []}))

    assert salida["tema_consulta"] is None
