"""
NuevaMente — Pruebas del filtro de la tabla de contenido.

Los textos imitan las guías de prueba ya normalizadas: las de europeanscrum.org
(entradas con «- N -») y la de Enterprise Agile Coach (esquema sin páginas).

Ejecutar:  pytest tests/test_rag_tabla_de_contenido.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.tabla_de_contenido import (  # noqa: E402
    es_encabezado_de_indice,
    quitar_tabla_de_contenido,
)

PORTADA = "GUÍA SCRUM MASTER\n2025\nv.1.0"
INDICE_1 = (
    "1 Tableof Contents\n"
    "2 Objetivos de la Guía - 3 -\n"
    "3 El Verdadero Rol del Scrum Master - 3 -\n"
    "4 Scrum: Mucho más que un marco de trabajo ligero - 3 -"
)
INDICE_2 = "19 Scrum Master ante la crisis - 9 -\n20 Ética del Scrum Master - 10 -\n31 Agradecimientos - 12 -"
CONTENIDO = (
    "2 Objetivos de la Guía\n"
    "Esta guía ofrece una visión completa del rol del Scrum Master.\n"
    "3 El Verdadero Rol del Scrum Master\n"
    "El Scrum Master es un líder al servicio del equipo."
)

ESQUEMA_1 = (
    "Guía Experta de Enterprise Agile\nCoach\n2024\nÍndice\n"
    "1. Introducción a Agile y su Importancia en la Empresa\n"
    "- 1.1. ¿Qué es Agile?\n- 1.2. Historia y evolución de Agile\n"
    "2. Principios y Valores de Agile"
)
ESQUEMA_2 = (
    "5. Implementación de Agile a Nivel Empresarial\n"
    "- 5.1. Evaluación de madurez Agile\n- 5.2. Estrategias para la adopción de Agile\n"
    "10. Conclusiones y Recomendaciones Finales"
)
CONTENIDO_ESQUEMA = (
    "1. Introducción a Agile y su Importancia en la\nEmpresa\n1.1. ¿Qué es Agile?\n"
    "Agile es un conjunto de metodologías y prácticas de desarrollo de software."
)


def test_quita_el_indice_con_numeros_de_pagina_aunque_cruce_paginas():
    assert quitar_tabla_de_contenido([PORTADA, INDICE_1, INDICE_2, CONTENIDO]) == [PORTADA, "", "", CONTENIDO]


def test_los_titulos_del_contenido_no_se_confunden_con_el_indice():
    # «2 Objetivos de la Guía» está en el índice y también como título del contenido.
    assert quitar_tabla_de_contenido([INDICE_1, CONTENIDO])[1] == CONTENIDO


def test_menos_de_tres_entradas_seguidas_no_son_un_indice():
    pagina = "Resumen - 3 -\nConclusión - 4 -\nTexto normal del capítulo, sin índice."
    assert quitar_tabla_de_contenido([pagina]) == [pagina]


def test_quita_el_indice_sin_numeros_si_lo_anuncia_un_encabezado():
    limpias = quitar_tabla_de_contenido([ESQUEMA_1, ESQUEMA_2, CONTENIDO_ESQUEMA])
    assert limpias == ["Guía Experta de Enterprise Agile\nCoach\n2024", "", CONTENIDO_ESQUEMA]


def test_las_listas_numeradas_del_contenido_no_se_tocan():
    pagina = "Pasos para priorizar:\n1. Listar los ítems\n2. Estimar el valor\n3. Ordenar\n4. Revisar con el equipo"
    assert quitar_tabla_de_contenido([pagina]) == [pagina]


def test_un_encabezado_sin_esquema_debajo_se_queda():
    pagina = "Índice\nEl índice de satisfacción del cliente subió este trimestre."
    assert quitar_tabla_de_contenido([pagina]) == [pagina]


def test_las_paginas_sin_indice_vuelven_iguales():
    paginas = ["\nTexto con un salto al comienzo\n", "Otra página", ""]
    assert quitar_tabla_de_contenido(paginas) == paginas


def test_tambien_funciona_con_el_texto_en_una_sola_pieza():
    texto = f"{PORTADA}\n\n{INDICE_1}\n{INDICE_2}\n\n{CONTENIDO}"
    [limpio] = quitar_tabla_de_contenido([texto])
    assert "- 3 -" not in limpio and "Tableof" not in limpio
    assert limpio.startswith(PORTADA) and limpio.endswith(CONTENIDO)


@pytest.mark.parametrize(
    "linea", ["1 Tableof Contents", "Table of Contents", "Índice", "INDICE", "Tabla de contenidos", "Contenido:"]
)
def test_reconoce_los_encabezados_de_indice(linea):
    assert es_encabezado_de_indice(linea)


@pytest.mark.parametrize("linea", ["Índice de satisfacción del cliente", "El contenido del Sprint", "2 Objetivos"])
def test_no_confunde_otros_titulos_con_un_encabezado_de_indice(linea):
    assert not es_encabezado_de_indice(linea)
