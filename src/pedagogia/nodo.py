from __future__ import annotations

from src.contracts import NivelDetalle, PerfilDestinatario

from .mapping import construir_especificacion_pedagogica


def preparar_explicacion_pedagogica(
    perfil: PerfilDestinatario,
    nivel_detalle: NivelDetalle,
) -> dict[str, object]:
    """
    Construye la especificación pedagógica pública que consumirá
    posteriormente la capa de orquestación.

    Esta función es determinística y no depende de AgentState,
    LangGraph, proveedores LLM ni servicios externos.

    La salida respeta el contrato pedagógico acordado:
    bloom, andamiaje, registro, foco y verbos.
    """
    spec = construir_especificacion_pedagogica(
        perfil=perfil,
        nivel_detalle=nivel_detalle,
    )

    return {
        "bloom": spec.bloom,
        "andamiaje": spec.andamiaje,
        "registro": spec.registro,
        "foco": spec.foco,
        "verbos": list(spec.verbos),
    }
