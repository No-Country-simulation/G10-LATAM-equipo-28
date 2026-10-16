"""
NuevaMente — Cuentas para calibrar el umbral de recuperación y las bandas de fidelidad.

Funciones puras sobre puntajes: el mejor coseno de cada consulta o afirmación
contra los chunks de su documento. No llaman a ninguna API; la medición con e5
la hace scripts/calibrar_e5.py.

Las sugerencias siguen reglas simples y a la vista. La decisión final de las
bandas es de la sesión del 06/10, con calibrar_bandas() de fidelidad/.

UMBRAL DE RECUPERACIÓN
  Si todo lo del tema queda por encima de todo lo ajeno, se sugiere el punto
  medio del hueco. Si se solapan, el corte con menos errores y, ante un empate,
  el más alto: es preferible pedir una aclaración de más que confirmar una
  fuente que no trata el tema.

BANDAS DE LA CASCADA DE FIDELIDAD
  Coseno >= alta: soportada sin juez. Coseno < baja: no soportada sin juez.
  En medio: decide el juez LLM. Las reglas de la sugerencia:
    - ninguna afirmación inventada se aprueba sin juez:  alta > máx(inventadas);
    - ninguna afirmación anclada se rechaza sin juez:     baja <= mín(ancladas).
  Si ancladas e inventadas no se solapan, la zona dudosa es el hueco entre ellas.

REESCALADO (propuesta c, aprobada el 29/09)
  Sin juez, la zona dudosa hoy usa el coseno crudo como puntaje; con e5, que
  nunca baja de ~0,73, eso infla el puntaje del paquete. El reescalado lleva el
  coseno a 0-1 con las bandas calibradas: (coseno - baja) / (alta - baja),
  recortado entre 0 y 1.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np

EPSILON = 0.005

SOPORTADA = "soportada"
DUDOSA = "dudosa"
NO_SOPORTADA = "no_soportada"


@dataclass(frozen=True)
class Resumen:
    n: int
    minimo: float
    p10: float
    mediana: float
    p90: float
    maximo: float

    def como_dict(self) -> dict[str, float]:
        return asdict(self)


def _numeros(valores: Sequence[float], nombre: str) -> list[float]:
    datos = [float(v) for v in valores]
    if not datos:
        raise ValueError(f"'{nombre}' no puede estar vacío")
    return datos


def resumir(valores: Sequence[float]) -> Resumen:
    """Cantidad, mínimo, percentiles 10, 50 y 90, y máximo."""
    datos = np.array(_numeros(valores, "valores"))
    return Resumen(
        n=len(datos),
        minimo=round(float(datos.min()), 4),
        p10=round(float(np.percentile(datos, 10)), 4),
        mediana=round(float(np.median(datos)), 4),
        p90=round(float(np.percentile(datos, 90)), 4),
        maximo=round(float(datos.max()), 4),
    )


# =============================================================================
# Umbral de recuperación
# =============================================================================


def contar_errores_umbral(umbral: float, tema: Sequence[float], ajenas: Sequence[float]) -> dict[str, int]:
    """Consultas del tema que quedarían afuera y consultas ajenas que pasarían."""
    return {
        "errores_tema": sum(t < umbral for t in tema),
        "errores_ajenas": sum(a >= umbral for a in ajenas),
    }


def sugerir_umbral(tema: Sequence[float], ajenas: Sequence[float], *, paso: float = EPSILON) -> dict:
    """Umbral de recuperación sugerido (ver las reglas en el docstring del módulo)."""
    tema = _numeros(tema, "tema")
    ajenas = _numeros(ajenas, "ajenas")
    minimo_tema, maximo_ajenas = min(tema), max(ajenas)
    margen = round(minimo_tema - maximo_ajenas, 4)

    if minimo_tema > maximo_ajenas:
        umbral = round((minimo_tema + maximo_ajenas) / 2, 4)
        return {"umbral": umbral, "separa": True, "margen": margen, **contar_errores_umbral(umbral, tema, ajenas)}

    todos = tema + ajenas
    pasos = int(round((max(todos) - min(todos)) / paso)) + 1
    candidatos = [round(min(todos) + i * paso, 6) for i in range(pasos + 1)]
    mejor_errores, umbral = None, candidatos[0]
    for candidato in candidatos:
        errores = sum(contar_errores_umbral(candidato, tema, ajenas).values())
        if mejor_errores is None or errores <= mejor_errores:  # <=: ante empate, el más alto
            mejor_errores, umbral = errores, candidato
    umbral = round(umbral, 4)
    return {"umbral": umbral, "separa": False, "margen": margen, **contar_errores_umbral(umbral, tema, ajenas)}


# =============================================================================
# Bandas de la cascada de fidelidad
# =============================================================================


def _piso(valor: float) -> float:
    """Redondea hacia abajo a 4 decimales (la tolerancia absorbe el ruido del punto flotante)."""
    return round(math.floor(valor * 10_000 + 1e-9) / 10_000, 4)


def _techo(valor: float) -> float:
    """Redondea hacia arriba a 4 decimales."""
    return round(math.ceil(valor * 10_000 - 1e-9) / 10_000, 4)


def sugerir_bandas(ancladas: Sequence[float], inventadas: Sequence[float], *, epsilon: float = EPSILON) -> dict:
    """
    Bandas sugeridas para la cascada (ver las reglas en el docstring del módulo).

    Se redondea siempre hacia el lado seguro: la baja hacia abajo (para no
    rechazar una anclada por un decimal) y la alta hacia arriba (para no
    aprobar una inventada).
    """
    ancladas = _numeros(ancladas, "ancladas")
    inventadas = _numeros(inventadas, "inventadas")
    minimo_ancladas, maximo_inventadas = min(ancladas), max(inventadas)
    sobre_inventadas = _techo(maximo_inventadas + epsilon)  # la alta nunca puede bajar de aquí
    bajo_ancladas = _piso(minimo_ancladas)  # la baja nunca puede subir de aquí
    margen = round(minimo_ancladas - maximo_inventadas, 4)
    if bajo_ancladas >= sobre_inventadas:
        # Hay un hueco de al menos epsilon: lo del hueco va al juez.
        return {"baja": sobre_inventadas, "alta": bajo_ancladas, "separa": True, "margen": margen}
    return {"baja": bajo_ancladas, "alta": sobre_inventadas, "separa": minimo_ancladas > maximo_inventadas,
            "margen": margen}


def clasificar(puntaje: float, baja: float, alta: float) -> str:
    """Veredicto de la cascada solo por coseno."""
    if puntaje >= alta:
        return SOPORTADA
    if puntaje < baja:
        return NO_SOPORTADA
    return DUDOSA


def efecto_de_bandas(ancladas: Sequence[float], inventadas: Sequence[float], baja: float, alta: float) -> dict:
    """Qué haría la cascada con esas bandas: aciertos, errores sin juez y llamadas al juez."""

    def contar(valores: Sequence[float]) -> dict[str, int]:
        cuenta = {SOPORTADA: 0, DUDOSA: 0, NO_SOPORTADA: 0}
        for valor in valores:
            cuenta[clasificar(valor, baja, alta)] += 1
        return cuenta

    de_ancladas, de_inventadas = contar(ancladas), contar(inventadas)
    al_juez = de_ancladas[DUDOSA] + de_inventadas[DUDOSA]
    total = len(ancladas) + len(inventadas)
    return {
        "baja": baja,
        "alta": alta,
        "ancladas": de_ancladas,
        "inventadas": de_inventadas,
        "inventadas_aprobadas_sin_juez": de_inventadas[SOPORTADA],
        "ancladas_rechazadas_sin_juez": de_ancladas[NO_SOPORTADA],
        "llamadas_al_juez": al_juez,
        "fraccion_al_juez": round(al_juez / total, 3) if total else 0.0,
    }


def reescalar(coseno: float, baja: float, alta: float) -> float:
    """Lleva el coseno a 0-1 con las bandas: (coseno - baja) / (alta - baja), recortado."""
    if alta <= baja:
        return 1.0 if coseno >= alta else 0.0
    return float(min(1.0, max(0.0, (coseno - baja) / (alta - baja))))


def puntaje_sin_juez(puntajes: Sequence[float], baja: float, alta: float, *, reescalado: bool) -> float:
    """
    anclaje_fuente_score que daría la cascada sin juez LLM (modo desarrollo).

    Soportada vale 1 y no soportada 0; en la zona dudosa se usa el coseno crudo
    (como hoy) o el reescalado (propuesta c).
    """
    valores = []
    for puntaje in _numeros(puntajes, "puntajes"):
        veredicto = clasificar(puntaje, baja, alta)
        if veredicto == SOPORTADA:
            valores.append(1.0)
        elif veredicto == NO_SOPORTADA:
            valores.append(0.0)
        else:
            valores.append(reescalar(puntaje, baja, alta) if reescalado else puntaje)
    return round(sum(valores) / len(valores), 4)
