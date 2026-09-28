"""Protocolos compartidos por los agentes de NuevaMente.

Definen la forma de las dependencias que cada agente recibe **inyectadas**, para
no acoplarse a un proveedor de LLM ni a una implementación concreta. Los tests
usan dobles (`FakeGenerator`, `FakeRecuperador`) que cumplen estos contratos.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class GeneradorEstructurado(Protocol):
    """Cualquier objeto con un `async generate(prompt, output_model)` sirve."""

    async def generate(self, *, prompt: str, output_model: type[BaseModel]) -> Any:
        """Produce una salida estructurada validable contra `output_model`."""
