"""
NuevaMente — Verificación de fidelidad a la fuente.

Es el diferenciador del producto: el sistema no solo genera contenido, mide y
muestra cuánto de lo que generó se sostiene en el documento original.

Integra en cascada los dos métodos que estaban en conflicto entre la
especificación de Frank (similitud coseno) y la decisión D-02 del equipo
(verificador LLM). Ver `nucleo.py` para el detalle del diseño.
"""

from .extraccion import (
    campos_verificables,
    extraer_afirmaciones,
    extraer_afirmaciones_de_items,
    resumen_de_cobertura,
)
from .nucleo import (
    BANDA_ALTA,
    BANDA_BAJA,
    Afirmacion,
    Chunk,
    Embeder,
    JuezLLM,
    ResultadoFidelidad,
    Veredicto,
    calcular_fidelidad,
    calibrar_bandas,
    coseno,
)

__all__ = [
    "BANDA_ALTA",
    "BANDA_BAJA",
    "Afirmacion",
    "Chunk",
    "Embeder",
    "JuezLLM",
    "ResultadoFidelidad",
    "Veredicto",
    "calcular_fidelidad",
    "calibrar_bandas",
    "campos_verificables",
    "coseno",
    "extraer_afirmaciones",
    "extraer_afirmaciones_de_items",
    "resumen_de_cobertura",
]
