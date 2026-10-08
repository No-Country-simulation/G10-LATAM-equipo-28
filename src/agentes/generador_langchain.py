"""Adaptador que expone un modelo de chat de LangChain como `GeneradorEstructurado`.

Es la pieza que conecta los agentes (que esperan `async generate(*, prompt,
output_model)`) con un modelo LangChain real. **No construye el modelo**: lo
recibe ya armado por inyección, así el agente no se acopla a un proveedor y este
archivo no nombra ninguno. Da igual si el modelo viene de `llm_provider.get_llm()`,
del cliente compartido de `seguridad/` o de un doble de test.

Uso típico:

    generador = GeneradorLangchain(get_llm())
    intencion = await clasificar_intencion(mensaje, tema_chat, generador)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from src.errores import ErrorLLM


class GeneradorLangchain:
    """Envuelve un chat model de LangChain con `with_structured_output`.

    `method` se propaga tal cual al backend (None = default del backend).
    Existe porque no todos los proveedores OpenAI-compatibles soportan el
    default: DeepSeek rechaza `json_schema` con error 400 y necesita
    `method="function_calling"`.
    """

    def __init__(self, modelo: Any, method: str | None = None) -> None:
        self._modelo = modelo
        self._method = method

    async def generate(self, *, prompt: str, output_model: type[BaseModel]) -> Any:
        """Pide al modelo una respuesta validable contra `output_model`.

        Devuelve el objeto estructurado tal como lo entrega LangChain (dict o
        instancia de `output_model`, según el modelo). La validación final la
        hace el agente, que es quien conoce su propio contrato de salida.
        """
        try:
            estructurado = self._modelo.with_structured_output(
                output_model, method=self._method
            )
            return await estructurado.ainvoke(prompt)
        except ErrorLLM:
            raise
        except Exception as exc:
            raise ErrorLLM(
                f"El modelo no devolvió una salida estructurada válida: {exc}"
            ) from exc
