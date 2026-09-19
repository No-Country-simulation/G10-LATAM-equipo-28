from __future__ import annotations

from src.contracts import NivelDetalle, PerfilDestinatario

from .mapping import construir_especificacion_pedagogica
from .prompts import construir_fragmento_prompt_pedagogico


def preparar_explicacion_pedagogica(
    perfil: PerfilDestinatario,
    nivel_detalle: NivelDetalle,
) -> dict[str, object]:
    """
    Construye la salida pedagógica que posteriormente consumirá
    el nodo LangGraph `explicacion_pedagogica`.

    Esta función no depende de AgentState ni del grafo.
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
        "verbos_recomendados": list(spec.verbos_recomendados),
        "instrucciones_redactor": construir_fragmento_prompt_pedagogico(spec),
    }
