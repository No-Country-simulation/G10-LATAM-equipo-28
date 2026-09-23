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

def test_fragmento_prompt_contiene_parametros_pedagogicos():
    from src.pedagogia import construir_fragmento_prompt_pedagogico

    spec = construir_especificacion_pedagogica(
        PerfilDestinatario.LIDER_TECNICO,
        NivelDetalle.ESTANDAR,
    )

    prompt = construir_fragmento_prompt_pedagogico(spec)

    assert "Evaluar" in prompt
    assert "Bajo" in prompt
    assert "Técnico-estratégico" in prompt
    assert "Criterio de decisión" in prompt
    assert "evaluar, comparar, justificar" in prompt


def test_fragmento_prompt_preserva_fidelidad_a_fuente():
    from src.pedagogia import construir_fragmento_prompt_pedagogico

    spec = construir_especificacion_pedagogica(
        PerfilDestinatario.PRINCIPIANTE,
        NivelDetalle.DIDACTICO,
    )

    prompt = construir_fragmento_prompt_pedagogico(spec)

    assert "no autorizan a agregar información" in prompt
    assert "respaldada por la fuente" in prompt


def test_preparar_explicacion_pedagogica():
    from src.pedagogia import preparar_explicacion_pedagogica

    salida = preparar_explicacion_pedagogica(
        PerfilDestinatario.LIDER_TECNICO,
        NivelDetalle.ESTANDAR,
    )

    assert salida["bloom"] == "Evaluar"
    assert salida["andamiaje"] == "Bajo"
    assert salida["registro"] == "Técnico-estratégico"
    assert salida["foco"] == "Criterio de decisión"
    assert salida["verbos"] == [
        "evaluar",
        "comparar",
        "justificar",
    ]


def test_salida_pedagogica_cumple_contrato_publico():
    from src.pedagogia import preparar_explicacion_pedagogica

    salida = preparar_explicacion_pedagogica(
        PerfilDestinatario.PRINCIPIANTE,
        NivelDetalle.DIDACTICO,
    )

    assert set(salida) == {
        "bloom",
        "andamiaje",
        "registro",
        "foco",
        "verbos",
    }
    assert salida["bloom"] == "Entender"
    assert salida["verbos"] == [
        "explicar",
        "identificar",
        "describir",
    ]
    assert "verbos_recomendados" not in salida
    assert "instrucciones_redactor" not in salida
