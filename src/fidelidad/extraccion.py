"""
NuevaMente — Extracción de afirmaciones verificables del paquete generado.

Aquí vuelve a rendir el contrato tipado: **cada formato tiene campos distintos,
y no todos son verificables**.

Ejemplos de lo que NO se verifica:
  · `pista_didactica` de una Flashcard es una analogía inventada a propósito
    ("piénsalo como un barrio cercado"). Medirla contra la fuente daría un falso
    positivo de alucinación en cada tarjeta.
  · `introduccion_contextualizada` es intencionalmente libre.
  · `titulo` es una etiqueta, no una afirmación.

Si se verificara todo por igual, el score castigaría justo lo que hace bueno al
material didáctico. Por eso la extracción es consciente del formato.
"""

from __future__ import annotations

from typing import Any

from ..contracts import FormatoSalida, PaqueteEducativo
from .nucleo import Afirmacion

# =============================================================================
# Qué campos de cada formato son afirmaciones técnicas verificables
# =============================================================================

_CAMPOS_VERIFICABLES: dict[FormatoSalida, tuple[str, ...]] = {
    # "dorso" es la respuesta factual. "frente" es la pregunta y
    # "pista_didactica" es una analogía deliberada: no se verifican.
    FormatoSalida.FLASHCARDS: ("dorso",),
    # "instruccion" y "resultado_esperado" describen el procedimiento real.
    # "advertencia" también, cuando existe.
    FormatoSalida.TUTORIAL: ("instruccion", "resultado_esperado", "advertencia"),
    # "punto_clave" es el hecho; "implicacion" y "relevancia_negocio" son
    # interpretación legítima del hecho, no se miden contra la fuente.
    FormatoSalida.RESUMEN_EJECUTIVO: ("punto_clave",),
    # La justificación es lo que afirma por qué la respuesta es correcta.
    FormatoSalida.QUIZ: ("justificacion",),
    # "guion" es el texto que dice el instructor; "apoyo_visual" es
    # sugerencia creativa.
    FormatoSalida.GUION_CLASE: ("guion",),
}

#: Por debajo de esto, el texto es demasiado corto para evaluar anclaje.
LONGITUD_MINIMA = 25


def extraer_afirmaciones(paquete: PaqueteEducativo) -> list[Afirmacion]:
    """
    Saca del paquete las afirmaciones que tiene sentido contrastar con la fuente.

    Conserva el `anclaje` que el Redactor declaró en cada ítem: sirve para que
    el verificador LLM reciba los chunks correctos en vez de los más parecidos.
    """
    return extraer_afirmaciones_de_items(
        paquete.metadatos.formato_generado, paquete.contenido_adaptado.items
    )


def extraer_afirmaciones_de_items(
    formato: FormatoSalida | str, items: list[dict[str, Any]]
) -> list[Afirmacion]:
    """
    Igual que `extraer_afirmaciones`, pero sin el paquete completo.

    Es la que usa el Revisor: cuando revisa, todavía no existe un
    `PaqueteEducativo` (falta `almacenamiento_oci`, que solo se conoce en
    Guardado). Le basta con el formato pedido y los ítems del borrador.
    """
    formato = FormatoSalida(formato)
    campos = _CAMPOS_VERIFICABLES.get(formato, ())
    afirmaciones: list[Afirmacion] = []

    for i, item in enumerate(items):
        anclaje = tuple(item.get("anclaje") or ())
        for campo in campos:
            texto = item.get(campo)
            if isinstance(texto, str) and len(texto.strip()) >= LONGITUD_MINIMA:
                afirmaciones.append(
                    Afirmacion(
                        texto=texto.strip(),
                        item_indice=i,
                        campo=campo,
                        anclaje_declarado=anclaje,
                    )
                )
    return afirmaciones


def campos_verificables(formato: FormatoSalida) -> tuple[str, ...]:
    """Para que la UI pueda marcar en pantalla qué se verificó y qué no."""
    return _CAMPOS_VERIFICABLES.get(formato, ())


def resumen_de_cobertura(paquete: PaqueteEducativo) -> dict[str, Any]:
    """
    Cuánto del paquete se está verificando. Útil para el timeline y para ser
    honestos en la presentación: el score no cubre el 100% del texto, y decirlo
    es más sólido que dejar que lo pregunten.
    """
    formato = paquete.metadatos.formato_generado
    afirmaciones = extraer_afirmaciones(paquete)
    total_campos = sum(
        1
        for item in paquete.contenido_adaptado.items
        for v in item.values()
        if isinstance(v, str) and len(v.strip()) >= LONGITUD_MINIMA
    )
    return {
        "formato": formato.value,
        "campos_verificados": list(campos_verificables(formato)),
        "afirmaciones_extraidas": len(afirmaciones),
        "campos_de_texto_totales": total_campos,
    }
