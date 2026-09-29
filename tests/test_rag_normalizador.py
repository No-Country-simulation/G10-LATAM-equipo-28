"""
NuevaMente — Pruebas del normalizador de texto.

Todos los casos de "cortes reales" salieron de la extraccion efectiva de los
PDFs de `Insumos NewMind`. No son inventados.

Ejecutar:  pytest tests/test_rag_normalizador.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.normalizador import (  # noqa: E402
    limpiar_simbolos,
    normalizar,
    normalizar_espacios,
    normalizar_paginas,
    normalizar_por_pagina,
    quitar_encabezado_repetido,
    quitar_ruido_de_linea,
    separar_numero_de_pagina_pegado,
    unir_guiones_de_corte,
    unir_palabras_partidas,
)


# =============================================================================
# 1. Cortes reales observados en los PDFs de prueba
# =============================================================================


@pytest.mark.parametrize(
    "roto,esperado",
    [
        ("Resp onsabilidades", "Responsabilidades"),
        ("Maste r", "Master"),
        ("ex pectativas", "expectativas"),
        ("im pacto", "impacto"),
        ("quié n", "quién"),
    ],
)
def test_repara_cortes_reales(roto, esperado):
    assert unir_palabras_partidas(roto) == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "de la organizacion",
        "El Scrum Master",
        "scrum masters",
        "mejora continua",
        "con el equipo",
        "para el Product Owner",
    ],
)
def test_no_rompe_texto_correcto(texto):
    """Lo mas importante: preferimos dejar un corte antes que fusionar mal."""
    assert unir_palabras_partidas(texto) == texto


@pytest.mark.parametrize(
    "caso,motivo",
    [
        ("influy e", "'e' es conjuncion valida: unir romperia 'trabajo e informe'"),
        ("sistémi cos", "resto de 3 letras: unir romperia 'Contenido uno'"),
    ],
)
def test_limitaciones_documentadas(caso, motivo):
    """
    LIMITACIONES A PROPOSITO, no bugs.

    Las dos reglas son conservadoras por diseno. Estos cortes quedan sin
    reparar porque la version que los arreglaba tambien corrompia texto
    correcto, y ese error es mas caro: un corte sin reparar degrada un
    embedding, pero una fusion incorrecta inventa una palabra que no existe
    en el documento fuente.
    """
    assert unir_palabras_partidas(caso) == caso, motivo


# =============================================================================
# 2. Simbolos
# =============================================================================


def test_convierte_la_vineta_corrupta():
    """Las guias de europeanscrum.org devuelven "¥" donde va una vineta."""
    assert limpiar_simbolos("¥ Con el equipo") == "- Con el equipo"


def test_limpiar_simbolos_no_inserta_caracteres():
    """
    Regresion de un bug real: una clave vacia en el diccionario de reemplazos
    hacia que str.replace("") insertara un guion entre CADA caracter, y el
    texto crecia cuatro veces.
    """
    original = "El Scrum Master facilita el trabajo del equipo."
    assert len(limpiar_simbolos(original)) <= len(original)


def test_normaliza_comillas_tipograficas():
    assert limpiar_simbolos("“Scrum”") == '"Scrum"'


# =============================================================================
# 3. Ruido de pagina
# =============================================================================


@pytest.mark.parametrize("linea", ["- 4 -", "12", "www.europeanscrum.org", "Pagina 3 de 20", "-----"])
def test_quita_lineas_de_ruido(linea):
    assert quitar_ruido_de_linea(f"Contenido real\n{linea}\nMas contenido") == (
        "Contenido real\nMas contenido"
    )


def test_separa_numero_pegado_al_titulo():
    """Caso real: "- 4 - 5 Responsabilidades" en la pagina 5 del PDF."""
    assert separar_numero_de_pagina_pegado("- 4 - 5 Responsabilidades") == "5 Responsabilidades"


def test_quita_encabezado_repetido_entre_paginas():
    paginas = [f"www.europeanscrum.org\nContenido {i}\n- {i} -" for i in range(1, 6)]
    limpias = quitar_encabezado_repetido(paginas)
    assert all("europeanscrum" not in p for p in limpias)
    assert all(f"Contenido {i}" in limpias[i - 1] for i in range(1, 6))


def test_con_pocas_paginas_no_toca_nada():
    """Con menos de 3 paginas no hay evidencia de repeticion: no se adivina."""
    paginas = ["Titulo\nContenido", "Otro"]
    assert quitar_encabezado_repetido(paginas) == paginas


# =============================================================================
# 4. Guiones de corte y espaciado
# =============================================================================


def test_une_palabra_cortada_por_guion():
    assert unir_guiones_de_corte("organi-\nzacion") == "organizacion"


def test_colapsa_espacios_y_saltos():
    assert normalizar_espacios("hola    mundo\n\n\n\nadios") == "hola mundo\n\nadios"


# =============================================================================
# 5. El pipeline completo
# =============================================================================


def test_pipeline_sobre_el_fragmento_real():
    """El fragmento tal cual sale de la pagina 5 del PDF de Scrum Master."""
    crudo = (
        " \n    \n www.europeanscrum.org \n"
        "- 4 - 5 Resp onsabilidades del Scrum Maste r \n"
        "¥ Con el equipo de desarrollo: fomenta la autogestion, gestionar ex pectativas \n"
    )
    limpio = normalizar(crudo)

    assert "Responsabilidades" in limpio
    assert "Master" in limpio
    assert "expectativas" in limpio
    assert "¥" not in limpio
    assert "www.europeanscrum.org" not in limpio
    assert "- 4 -" not in limpio


def test_el_pipeline_nunca_agranda_el_texto():
    """Guarda contra la clase de bug que multiplico el texto por cuatro."""
    crudo = "www.europeanscrum.org\n- 4 -\nEl Scrum Master facilita.\n¥ Punto uno.\n" * 20
    assert len(normalizar(crudo)) < len(crudo)


def test_normalizar_paginas_acepta_lista_vacia():
    assert normalizar_paginas([]) == ""


def test_normalizar_tolera_pagina_sin_texto():
    """Uno de los PDFs reales tiene una pagina sin texto extraible."""
    limpio = normalizar_paginas(["Contenido uno", "", "   ", "Contenido dos"])
    assert "Contenido uno" in limpio and "Contenido dos" in limpio


# =============================================================================
# 6. Normalizar conservando las paginas (lo usa el chunking)
# =============================================================================


def test_normalizar_por_pagina_conserva_la_cantidad_de_paginas():
    paginas = ["Contenido uno", "", "   ", "Contenido dos"]
    resultado = normalizar_por_pagina(paginas)
    assert resultado == ["Contenido uno", "", "", "Contenido dos"]


def test_normalizar_por_pagina_quita_el_encabezado_repetido():
    paginas = [f"Guia oficial del Scrum Master\nContenido de la pagina {i}" for i in range(4)]
    resultado = normalizar_por_pagina(paginas)
    assert all("Guia oficial" not in p for p in resultado)
    assert resultado[2] == "Contenido de la pagina 2"


def test_normalizar_por_pagina_repara_lo_mismo_que_normalizar():
    pagina = "- 4 - 5 Resp onsabilidades del Scrum Maste r"
    assert normalizar_por_pagina([pagina]) == [normalizar(pagina)]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v", "--tb=short"]))
