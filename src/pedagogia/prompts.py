from __future__ import annotations

from .mapping import EspecificacionPedagogica


def construir_fragmento_prompt_pedagogico(
    spec: EspecificacionPedagogica,
) -> str:
    """
    Convierte una especificación pedagógica en instrucciones explícitas
    para el Redactor Pedagógico.
    """
    verbos = ", ".join(spec.verbos_recomendados)

    return (
        "INSTRUCCIONES PEDAGÓGICAS:\n"
        f"- Nivel cognitivo (Bloom): {spec.bloom}\n"
        f"- Andamiaje: {spec.andamiaje}\n"
        f"- Registro lingüístico: {spec.registro}\n"
        f"- Foco pedagógico: {spec.foco}\n"
        f"- Verbos recomendados: {verbos}\n"
        "- Estas instrucciones modifican la forma de explicar, "
        "pero no autorizan a agregar información que no esté respaldada "
        "por la fuente."
    )
