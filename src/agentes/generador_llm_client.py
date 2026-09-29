"""Adapter fino entre el core async del Redactor y la API de llm_client de Franklin."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel


class GeneradorLLMClient:
    """Adapta ``get_llm(...).with_structured_output(...).invoke(...)``.

    La factory y el rate limiter se inyectan desde el composition root. Así este
    carril no importa, duplica ni modifica el cliente ni el limitador de Franklin.
    """

    def __init__(self, get_llm: Callable[..., Any], rate_limiter: Any) -> None:
        self._get_llm = get_llm
        self._rate_limiter = rate_limiter

    async def generate(self, *, prompt: str, output_model: type[BaseModel]) -> Any:
        """Solicita una respuesta estructurada usando la interfaz compartida."""
        messages: Sequence[Mapping[str, str]] = [{"role": "user", "content": prompt}]

        def _invoke() -> Any:
            llm = self._get_llm(mensajes=list(messages), rate_limiter=self._rate_limiter)
            runnable = llm.with_structured_output(output_model)
            result = runnable.invoke(list(messages))
            if isinstance(result, BaseModel):
                return result.model_dump(mode="json")
            return result

        return await asyncio.to_thread(_invoke)
