"""
NuevaMente — Cálculo de anclaje_fuente_score en cascada.

INTEGRA LOS DOS MÉTODOS QUE ESTABAN EN CONFLICTO
-----------------------------------------------
La especificación de Frank propone similitud coseno. La decisión D-02 del
equipo propone un verificador LLM independiente. No hay que elegir: **cada uno
es bueno en una zona distinta**, y se combinan en cascada.

    Para CADA afirmación generada:

      1. Coseno contra los chunks fuente  (gratis, determinista, siempre)
                    │
        ┌───────────┼───────────┐
        │           │           │
     sim >= 0.85  0.55-0.85   sim < 0.55
        │           │           │
     SOPORTADA   ¿dudoso?    NO SOPORTADA
     puntaje 1.0     │        puntaje 0.0
                     ▼
              2. Verificador LLM        (solo aquí: pocas llamadas)
                 soportada   -> 1.0
                 parcial     -> 0.5
                 no soportada-> 0.0

    score = suma de puntajes / cantidad de afirmaciones

POR QUÉ ESTO ES MEJOR QUE CUALQUIERA DE LOS DOS SOLO
----------------------------------------------------
· El coseno solo mide PARECIDO, no implicación: una alucinación bien redactada
  sobre el mismo tema puntúa alto. Pero es infalible en los extremos — si una
  afirmación no se parece a NINGÚN chunk, no salió de la fuente, punto.

· El verificador LLM sí evalúa si la afirmación SE DERIVA de la fuente, pero
  cuesta una llamada, no es determinista y depende de la cuota.

· En cascada, el LLM se gasta solo donde el coseno no es concluyente. En los
  documentos de prueba, la banda dudosa suele ser el 20-30% de las afirmaciones:
  se reduce el costo ~70% y se conserva el juicio donde hace falta.

· Para la demo en vivo: la mayoría de las afirmaciones se resuelven de forma
  DETERMINISTA. Menos varianza entre ensayo y presentación.

· Para el jurado: "medimos similitud primero, y cuando la similitud no alcanza
  para decidir, un agente independiente juzga si la afirmación realmente se
  desprende del documento". Es defendible sin letra pequeña.

DISEÑO
------
Las dependencias se INYECTAN (el embeder y el juez son callables). Así este
módulo se prueba entero sin modelo de embeddings ni LLM, y el equipo puede
cambiar cualquiera de los dos sin tocar esta lógica.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

# =============================================================================
# Tipos de las dependencias inyectadas
# =============================================================================

#: Convierte textos en vectores. Lo implementa src/rag/embeddings.py.
Embeder = Callable[[Sequence[str]], list[list[float]]]

#: Juzga UNA afirmación contra los chunks. Devuelve uno de:
#: "soportada" | "parcial" | "no_soportada".
#: Lo implementa el Crítico/Revisor con el LLM.
JuezLLM = Callable[[str, Sequence[str]], str]


# =============================================================================
# Datos
# =============================================================================


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    texto: str


@dataclass(frozen=True)
class Afirmacion:
    """Una afirmación verificable extraída del contenido generado."""

    texto: str
    item_indice: int
    campo: str
    #: IDs de chunk que el Redactor declaró en el campo `anclaje` del ítem.
    anclaje_declarado: tuple[str, ...] = ()


MetodoVeredicto = Literal["coseno_alto", "coseno_bajo", "verificador_llm"]


@dataclass(frozen=True)
class Veredicto:
    afirmacion: Afirmacion
    metodo: MetodoVeredicto
    similitud: float
    puntaje: float  # 1.0 soportada · 0.5 parcial · 0.0 no soportada
    chunk_mas_cercano: str | None
    detalle: str

    @property
    def sospechosa(self) -> bool:
        return self.puntaje < 1.0


@dataclass(frozen=True)
class ResultadoFidelidad:
    score: float
    veredictos: list[Veredicto] = field(default_factory=list)
    llamadas_al_llm: int = 0

    @property
    def evaluadas(self) -> int:
        return len(self.veredictos)

    @property
    def soportadas(self) -> float:
        return sum(v.puntaje for v in self.veredictos)

    @property
    def sospechosas(self) -> list[Veredicto]:
        return [v for v in self.veredictos if v.sospechosa]

    def supera(self, umbral: float) -> bool:
        return self.score >= umbral

    def a_evaluacion_calidad(self, observaciones: str, claridad: str) -> dict:
        """Arma el bloque `evaluacion_calidad` del contrato de salida."""
        return {
            "anclaje_fuente_score": round(self.score, 2),
            "claridad_pedagogica": claridad,
            "observaciones": observaciones,
            "afirmaciones_evaluadas": self.evaluadas,
            "afirmaciones_soportadas": int(self.soportadas),
        }

    def resumen(self) -> str:
        """Una línea para el timeline de la UI."""
        por_metodo: dict[str, int] = {}
        for v in self.veredictos:
            por_metodo[v.metodo] = por_metodo.get(v.metodo, 0) + 1
        detalle = " · ".join(f"{k}: {n}" for k, n in sorted(por_metodo.items()))
        return (
            f"anclaje {self.score:.2f} — {self.evaluadas} afirmaciones "
            f"({detalle}) · {self.llamadas_al_llm} llamadas al LLM"
        )


# =============================================================================
# Similitud coseno, sin dependencias
# =============================================================================


def coseno(a: Sequence[float], b: Sequence[float]) -> float:
    """Similitud coseno entre dos vectores. Devuelve 0.0 si alguno es nulo."""
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return num / (na * nb)


# =============================================================================
# El cálculo en cascada
# =============================================================================

#: Por encima de esto, la afirmación se da por anclada sin consultar al LLM.
BANDA_ALTA = 0.85

#: Por debajo de esto, se da por NO anclada sin consultar al LLM.
BANDA_BAJA = 0.55

#: Estos dos valores hay que CALIBRARLOS con los documentos reales antes de
#: fijarlos. `calibrar_bandas()` ayuda a encontrarlos.

_PUNTAJE_LLM = {"soportada": 1.0, "parcial": 0.5, "no_soportada": 0.0}


def calcular_fidelidad(
    afirmaciones: Sequence[Afirmacion],
    chunks: Sequence[Chunk],
    embeder: Embeder,
    juez_llm: JuezLLM | None = None,
    *,
    vectores_chunks: Sequence[Sequence[float]] | None = None,
    banda_alta: float = BANDA_ALTA,
    banda_baja: float = BANDA_BAJA,
) -> ResultadoFidelidad:
    """
    Calcula `anclaje_fuente_score` combinando coseno y verificador LLM.

    Si `juez_llm` es None, la banda dudosa se resuelve con el coseno crudo
    (puntaje = similitud). Sirve para desarrollo y para el modo "sin LLM".

    `vectores_chunks` (recomendado en producción): los vectores de los chunks
    tal como ya están guardados en Chroma, en el mismo orden que `chunks`.
    Con embeddings por API, recalcularlos gasta cuota por cada chunk en cada
    verificación. Si no se pasan, se calculan con `embeder`.

    Prefijos de e5: los modelos `multilingual-e5-*` esperan "query: " y
    "passage: " delante del texto. Eso lo maneja `src/rag/embeddings.py`, no
    este módulo. La forma correcta es: chunks indexados con "passage: " (sus
    vectores salen de Chroma vía `vectores_chunks`) y afirmaciones embebidas
    con "query: " (el `embeder` que se pasa aquí).
    """
    if vectores_chunks is not None and len(vectores_chunks) != len(chunks):
        raise ValueError(
            f"vectores_chunks tiene {len(vectores_chunks)} vectores y chunks "
            f"tiene {len(chunks)}: deben venir en el mismo orden y cantidad."
        )
    if not afirmaciones:
        return ResultadoFidelidad(score=0.0)
    if not chunks:
        # Sin fuente no hay anclaje posible. No es un error: es score 0.
        return ResultadoFidelidad(
            score=0.0,
            veredictos=[
                Veredicto(a, "coseno_bajo", 0.0, 0.0, None, "No hay chunks fuente.")
                for a in afirmaciones
            ],
        )

    vec_afirmaciones = embeder([a.texto for a in afirmaciones])
    vec_chunks = (
        list(vectores_chunks)
        if vectores_chunks is not None
        else embeder([c.texto for c in chunks])
    )

    veredictos: list[Veredicto] = []
    llamadas = 0

    for afirmacion, va in zip(afirmaciones, vec_afirmaciones):
        mejor_sim, mejor_chunk = -1.0, None
        for chunk, vc in zip(chunks, vec_chunks):
            s = coseno(va, vc)
            if s > mejor_sim:
                mejor_sim, mejor_chunk = s, chunk

        # --- Zona alta: claramente anclada ---
        if mejor_sim >= banda_alta:
            veredictos.append(
                Veredicto(
                    afirmacion, "coseno_alto", mejor_sim, 1.0, mejor_chunk.chunk_id,
                    f"Similitud {mejor_sim:.2f} con {mejor_chunk.chunk_id}.",
                )
            )
            continue

        # --- Zona baja: claramente no anclada ---
        if mejor_sim < banda_baja:
            veredictos.append(
                Veredicto(
                    afirmacion, "coseno_bajo", mejor_sim, 0.0, mejor_chunk.chunk_id,
                    f"Similitud {mejor_sim:.2f}: por debajo de {banda_baja}. "
                    f"Posible alucinación.",
                )
            )
            continue

        # --- Zona dudosa: aquí sí vale la pena preguntarle al LLM ---
        if juez_llm is None:
            veredictos.append(
                Veredicto(
                    afirmacion, "coseno_bajo", mejor_sim, mejor_sim, mejor_chunk.chunk_id,
                    f"Zona dudosa ({mejor_sim:.2f}) sin verificador LLM: "
                    f"se usa la similitud cruda.",
                )
            )
            continue

        textos = _chunks_relevantes(afirmacion, chunks, vec_chunks, va)
        fallo = juez_llm(afirmacion.texto, textos)
        llamadas += 1
        puntaje = _PUNTAJE_LLM.get(fallo.strip().lower(), 0.0)
        veredictos.append(
            Veredicto(
                afirmacion, "verificador_llm", mejor_sim, puntaje, mejor_chunk.chunk_id,
                f"Zona dudosa ({mejor_sim:.2f}). El verificador dictaminó: {fallo}.",
            )
        )

    score = sum(v.puntaje for v in veredictos) / len(veredictos)
    return ResultadoFidelidad(score=score, veredictos=veredictos, llamadas_al_llm=llamadas)


def _chunks_relevantes(
    afirmacion: Afirmacion,
    chunks: Sequence[Chunk],
    vec_chunks: Sequence[Sequence[float]],
    vec_afirmacion: Sequence[float],
    top: int = 3,
) -> list[str]:
    """
    Los chunks que se le pasan al verificador LLM.

    Prioriza los que el Redactor declaró en `anclaje`; si no declaró ninguno,
    manda los más parecidos. Así el juez ve poco texto y del relevante.
    """
    if afirmacion.anclaje_declarado:
        declarados = [c.texto for c in chunks if c.chunk_id in afirmacion.anclaje_declarado]
        if declarados:
            return declarados[:top]

    ordenados = sorted(
        zip(chunks, vec_chunks),
        key=lambda par: coseno(vec_afirmacion, par[1]),
        reverse=True,
    )
    return [c.texto for c, _ in ordenados[:top]]


# =============================================================================
# Calibración de las bandas
# =============================================================================


def calibrar_bandas(
    ancladas: Sequence[float], alucinadas: Sequence[float]
) -> tuple[float, float]:
    """
    Sugiere `banda_alta` y `banda_baja` a partir de ejemplos etiquetados a mano.

    Uso: tomar ~20 afirmaciones que SÍ salen del documento y ~20 inventadas,
    calcular su similitud, y pasar las dos listas. Devuelve bandas que dejan
    la zona dudosa lo más pequeña posible sin mezclar los dos grupos.

    Es la única forma honesta de fijar estos números: elegirlos a ojo es
    inventar el diferenciador del producto.
    """
    if not ancladas or not alucinadas:
        return BANDA_ALTA, BANDA_BAJA
    banda_alta = max(alucinadas)      # por encima: ninguna alucinada llega
    banda_baja = min(ancladas)        # por debajo: ninguna real cae
    if banda_baja > banda_alta:       # separación perfecta
        medio = (banda_baja + banda_alta) / 2
        return medio, medio
    return banda_alta, banda_baja
