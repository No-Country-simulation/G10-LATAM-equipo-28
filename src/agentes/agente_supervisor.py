"""Agente Supervisor: clasifica la intención del usuario.

Núcleo puro y desacoplado. Recibe un generador estructurado por inyección y
devuelve un `IntencionOut`. No genera contenido educativo, no evalúa cobertura
del tema y no accede a OCI.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from src.contracts import (
    FormatoSalida,
    NichoSector,
    NivelDetalle,
    PerfilDestinatario,
)
from src.errores import ErrorLLM, ErrorSalidaInvalida
from src.prompts.supervisor import construir_prompt_supervisor

from .protocolos import GeneradorEstructurado


class IntencionOut(BaseModel):
    """Salida estructurada del Supervisor.

    Los cuatro parámetros usan los enums del contrato, que aceptan la forma
    larga y variantes con/sin tilde como alias. `None` = el usuario no lo indicó.
    """

    model_config = ConfigDict(extra="forbid")

    tema_consulta: str | None = None
    perfil_destinatario: PerfilDestinatario | None = None
    formato_salida: FormatoSalida | None = None
    nicho_sector: NichoSector | None = None
    nivel_detalle: NivelDetalle | None = None

    @field_validator("tema_consulta")
    @classmethod
    def _tema_no_vacio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        limpio = valor.strip()
        return limpio or None


async def clasificar_intencion(
    mensaje_usuario: str,
    tema_pedido_chat: str | None,
    generador: GeneradorEstructurado,
) -> IntencionOut:
    """Clasifica el pedido del usuario en un `IntencionOut`.

    Si el modelo no extrajo `tema_consulta`, se usa `tema_pedido_chat` como
    default de conveniencia (los campos siguen siendo independientes).
    """
    prompt = construir_prompt_supervisor(mensaje_usuario, tema_pedido_chat)

    try:
        bruto = await generador.generate(prompt=prompt, output_model=IntencionOut)
    except ErrorLLM:
        raise
    except Exception as exc:
        raise ErrorLLM("Falló la clasificación de intención del Supervisor.") from exc

    try:
        intencion = IntencionOut.model_validate(bruto)
    except (ValidationError, TypeError, ValueError) as exc:
        raise ErrorSalidaInvalida(
            f"La salida del Supervisor no cumple el contrato: {exc}"
        ) from exc

    if not intencion.tema_consulta and tema_pedido_chat:
        tema = tema_pedido_chat.strip() or None
        if tema:
            intencion = intencion.model_copy(update={"tema_consulta": tema})

    return intencion
