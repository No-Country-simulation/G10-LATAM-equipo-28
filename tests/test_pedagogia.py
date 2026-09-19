from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.contracts import NivelDetalle, PerfilDestinatario  # noqa: E402
from src.pedagogia import construir_especificacion_pedagogica  # noqa: E402


@pytest.mark.parametrize(
    ("perfil", "bloom", "andamiaje", "registro", "foco"),
    [
        (
            PerfilDestinatario.PRINCIPIANTE,
            "Entender",
            "Alto",
            "Cotidiano",
            "Comprensión conceptual",
        ),
        (
            PerfilDestinatario.DESARROLLADOR,
            "Aplicar",
            "Medio",
            "Técnico",
            "Ejecución práctica",
        ),
        (
            PerfilDestinatario.LIDER_TECNICO,
            "Evaluar",
            "Bajo",
            "Técnico-estratégico",
            "Criterio de decisión",
        ),
        (
            PerfilDestinatario.GESTOR_EJECUTIVO,
            "Entender",
            "Alto",
            "Ejecutivo",
            "Impacto en negocio",
        ),
    ],
)
def test_mapeo_pedagogico_por_perfil(
    perfil,
    bloom,
    andamiaje,
    registro,
    foco,
):
    spec = construir_especificacion_pedagogica(
        perfil,
        NivelDetalle.ESTANDAR,
    )

    assert spec.bloom == bloom
    assert spec.andamiaje == andamiaje
    assert spec.registro == registro
    assert spec.foco == foco
    assert spec.verbos_recomendados


def test_mapeo_pedagogico_es_deterministico():
    primera = construir_especificacion_pedagogica(
        PerfilDestinatario.PRINCIPIANTE,
        NivelDetalle.DIDACTICO,
    )
    segunda = construir_especificacion_pedagogica(
        PerfilDestinatario.PRINCIPIANTE,
        NivelDetalle.DIDACTICO,
    )

    assert primera == segunda
