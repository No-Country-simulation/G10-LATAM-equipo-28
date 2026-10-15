from __future__ import annotations

import json

import pytest

from src.contracts import FORMATOS_IMPLEMENTADOS_MVP, FormatoSalida, MODELO_ITEM_POR_FORMATO
from src.pedagogia import cargar_formatos_pedagogicos


def test_carga_las_cuatro_fichas_y_corresponden_al_contrato():
    fichas = cargar_formatos_pedagogicos()

    assert set(fichas) == set(FORMATOS_IMPLEMENTADOS_MVP)
    assert len(fichas) == 4
    for formato, ficha in fichas.items():
        assert ficha.formato is formato
        assert ficha.version == "1.0"
        assert set(ficha.campos_obligatorios) | set(ficha.campos_opcionales) == set(
            MODELO_ITEM_POR_FORMATO[formato].model_fields
        )
        assert ficha.reglas


@pytest.mark.parametrize(
    ("formato", "esperados"),
    [
        (FormatoSalida.FLASHCARDS, {"frente", "dorso", "pista_didactica"}),
        (
            FormatoSalida.TUTORIAL,
            {"paso_numero", "titulo_paso", "instruccion", "resultado_esperado"},
        ),
        (FormatoSalida.QUIZ, {"pregunta", "opciones", "respuesta_correcta", "justificacion"}),
        (
            FormatoSalida.RESUMEN_EJECUTIVO,
            {"punto_clave", "implicacion", "relevancia_negocio"},
        ),
    ],
)
def test_campos_requeridos_provienen_de_la_definicion_del_formato(formato, esperados):
    ficha = cargar_formatos_pedagogicos()[formato]

    assert esperados <= set(ficha.campos_obligatorios)


def test_catalogo_no_declara_guion_de_clase():
    fichas = cargar_formatos_pedagogicos()

    assert FormatoSalida.GUION_CLASE not in fichas


def test_error_legible_para_clave_desconocida(tmp_path):
    ficha = {
        "version": "1.0",
        "formato": "Flashcards",
        "nombre": "Flashcards",
        "campos_obligatorios": ["anclaje", "frente", "dorso", "pista_didactica"],
        "campos_opcionales": [],
        "reglas": ["Regla real del formato."],
        "fuente": "docs/02_Decision-gate_v2_RESUELTO.md §2.1",
        "sorpresa": True,
    }
    (tmp_path / "flashcards.json").write_text(json.dumps(ficha), encoding="utf-8")

    with pytest.raises(ValueError, match="claves desconocidas: \\['sorpresa'\\]"):
        cargar_formatos_pedagogicos(tmp_path)


def test_error_legible_para_campos_que_no_coinciden_con_el_modelo(tmp_path):
    ficha = {
        "version": "1.0",
        "formato": "Flashcards",
        "nombre": "Flashcards",
        "campos_obligatorios": ["anclaje", "frente", "dorso", "campo_inventado"],
        "campos_opcionales": [],
        "reglas": ["Regla real del formato."],
        "fuente": "docs/02_Decision-gate_v2_RESUELTO.md §2.1",
    }
    (tmp_path / "flashcards.json").write_text(json.dumps(ficha), encoding="utf-8")

    with pytest.raises(ValueError, match="campos no corresponden"):
        cargar_formatos_pedagogicos(tmp_path)
