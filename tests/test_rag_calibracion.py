"""
NuevaMente — Pruebas de las cuentas de calibración (umbral y bandas).

Ejecutar:  pytest tests/test_rag_calibracion.py -v
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.calibracion import (  # noqa: E402
    DUDOSA,
    NO_SOPORTADA,
    SOPORTADA,
    clasificar,
    contar_errores_umbral,
    efecto_de_bandas,
    puntaje_sin_juez,
    reescalar,
    resumir,
    sugerir_bandas,
    sugerir_umbral,
)

# Números de la prueba en vivo de T2-06 con la guía del Scrum Master.
TEMA_T206 = [0.8839, 0.8607, 0.8977]
AJENAS_T206 = [0.786, 0.7913]


def test_resumir():
    resumen = resumir([0.70, 0.80, 0.90])
    assert (resumen.n, resumen.minimo, resumen.mediana, resumen.maximo) == (3, 0.7, 0.8, 0.9)
    assert resumen.minimo <= resumen.p10 <= resumen.mediana <= resumen.p90 <= resumen.maximo
    with pytest.raises(ValueError):
        resumir([])


# =============================================================================
# Umbral de recuperación
# =============================================================================


def test_umbral_con_separacion_es_el_punto_medio():
    sugerencia = sugerir_umbral(TEMA_T206, AJENAS_T206)
    assert sugerencia["separa"] is True
    assert sugerencia["umbral"] == pytest.approx((0.8607 + 0.7913) / 2, abs=1e-4)
    assert sugerencia["margen"] == pytest.approx(0.0694, abs=1e-4)
    assert (sugerencia["errores_tema"], sugerencia["errores_ajenas"]) == (0, 0)


def test_umbral_con_solape_minimiza_errores_y_prefiere_el_mas_alto():
    sugerencia = sugerir_umbral([0.80, 0.85, 0.90], [0.78, 0.81])
    assert sugerencia["separa"] is False
    assert sugerencia["umbral"] == 0.85
    assert (sugerencia["errores_tema"], sugerencia["errores_ajenas"]) == (1, 0)


def test_contar_errores_del_umbral_viejo_y_del_nuevo():
    assert contar_errores_umbral(0.78, TEMA_T206, AJENAS_T206) == {"errores_tema": 0, "errores_ajenas": 2}
    assert contar_errores_umbral(0.82, TEMA_T206, AJENAS_T206) == {"errores_tema": 0, "errores_ajenas": 0}


def test_umbral_sin_datos():
    with pytest.raises(ValueError):
        sugerir_umbral([], [0.7])


# =============================================================================
# Bandas
# =============================================================================


def test_bandas_con_separacion_la_zona_dudosa_es_el_hueco():
    sugerencia = sugerir_bandas([0.88, 0.90], [0.80, 0.84])
    assert sugerencia == {"baja": 0.845, "alta": 0.88, "separa": True, "margen": 0.04}


def test_bandas_con_solape_cubren_el_solape():
    sugerencia = sugerir_bandas([0.83, 0.90], [0.79, 0.87])
    assert sugerencia["separa"] is False
    assert (sugerencia["baja"], sugerencia["alta"]) == (0.83, 0.875)


def test_las_bandas_sugeridas_nunca_aprueban_una_inventada_ni_rechazan_una_anclada():
    azar = random.Random(7)
    for _ in range(200):
        ancladas = [azar.uniform(0.75, 0.95) for _ in range(20)]
        inventadas = [azar.uniform(0.72, 0.92) for _ in range(20)]
        bandas = sugerir_bandas(ancladas, inventadas)
        efecto = efecto_de_bandas(ancladas, inventadas, bandas["baja"], bandas["alta"])
        assert efecto["inventadas_aprobadas_sin_juez"] == 0
        assert efecto["ancladas_rechazadas_sin_juez"] == 0


def test_clasificar():
    assert clasificar(0.90, baja=0.55, alta=0.85) == SOPORTADA
    assert clasificar(0.79, baja=0.55, alta=0.85) == DUDOSA
    assert clasificar(0.50, baja=0.55, alta=0.85) == NO_SOPORTADA


def test_con_las_bandas_de_hoy_lo_ajeno_nunca_se_rechaza_sin_juez():
    efecto = efecto_de_bandas([0.88, 0.90], [0.786, 0.7913], baja=0.55, alta=0.85)
    assert efecto["inventadas"] == {SOPORTADA: 0, DUDOSA: 2, NO_SOPORTADA: 0}
    assert efecto["llamadas_al_juez"] == 2
    assert efecto["fraccion_al_juez"] == 0.5


# =============================================================================
# Reescalado y puntaje sin juez
# =============================================================================


@pytest.mark.parametrize("coseno,esperado", [(0.79, 0.0), (0.80, 0.0), (0.84, 0.5), (0.88, 1.0), (0.95, 1.0)])
def test_reescalar(coseno, esperado):
    assert reescalar(coseno, baja=0.80, alta=0.88) == pytest.approx(esperado)


def test_reescalar_con_bandas_iguales():
    assert reescalar(0.9, baja=0.85, alta=0.85) == 1.0
    assert reescalar(0.8, baja=0.85, alta=0.85) == 0.0


def test_el_ejemplo_de_la_explicacion_del_29_09():
    # 7 afirmaciones soportadas y 3 inventadas y ajenas (coseno 0,79).
    paquete = [0.90] * 7 + [0.79] * 3
    assert puntaje_sin_juez(paquete, baja=0.55, alta=0.85, reescalado=False) == pytest.approx(0.937)
    assert puntaje_sin_juez(paquete, baja=0.80, alta=0.88, reescalado=True) == pytest.approx(0.70)
