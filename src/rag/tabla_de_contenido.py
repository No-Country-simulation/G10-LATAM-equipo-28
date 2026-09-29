"""
NuevaMente — Quita la tabla de contenido antes de dividir el documento.

En la calibración con e5 (29/09), los chunks del índice no fueron el mejor
chunk de ninguna consulta del tema ni de ninguna afirmación anclada, pero sí
de consultas ajenas o vecinas: «contratos ágiles» marcaba 0.824 contra el
índice de la guía del Scrum Master. Se reconocen dos formatos:

  1. Entradas con número de página al final («2 Objetivos de la Guía - 3 -»).
     Se quita cada corrida de al menos MIN_ENTRADAS seguidas, aunque cruce
     páginas, y el encabezado que la anuncia («Table of Contents», «Índice»).
  2. Esquema numerado sin números de página («1. Introducción», «- 1.1. ...»).
     Solo si un encabezado de índice lo anuncia en la misma página y al menos
     el 60 % de las líneas que le siguen son entradas; sigue en las páginas
     siguientes mientras el 80 % de sus líneas sean entradas.

Se quitan solo esas líneas: el resto de la página (la portada, por ejemplo)
queda, y las páginas sin índice vuelven iguales. Las listas numeradas del
contenido no se tocan: no llevan número de página ni un encabezado de índice.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

MIN_ENTRADAS = 3
_PROPORCION_EN_LA_PRIMERA_PAGINA = 0.6
_PROPORCION_EN_LAS_SIGUIENTES = 0.8

_CON_NUMERO_DE_PAGINA = re.compile(r"\s-\s?\d{1,3}\s?-\s*$")
_ENTRADA_DE_ESQUEMA = re.compile(r"^\s*(?:[-•o]\s*)?\d+(?:\.\d+)*\.?\s+\S")
_ENCABEZADO = re.compile(
    r"^\s*(?:\d+\s+)?"
    r"(?:table\s*of\s*contents|tabla\s+de\s+contenidos?|indice|contenidos?)\s*:?\s*$"
)


def es_encabezado_de_indice(linea: str) -> bool:
    """«Table of Contents», «Índice», «Tabla de contenido»... solos en la línea."""
    return bool(_ENCABEZADO.match(_sin_tildes(linea)))


def quitar_tabla_de_contenido(paginas: Sequence[str]) -> list[str]:
    """Devuelve las páginas sin las líneas del índice."""
    lineas = [pagina.split("\n") for pagina in paginas]
    quitar: list[set[int]] = [set() for _ in lineas]
    _marcar_entradas_con_numero_de_pagina(lineas, quitar)
    _marcar_esquema_anunciado(lineas, quitar)
    limpias = []
    for n, pagina in enumerate(paginas):
        if quitar[n]:
            quedan = (linea for i, linea in enumerate(lineas[n]) if i not in quitar[n])
            pagina = "\n".join(quedan).strip()
        limpias.append(pagina)
    return limpias


def _sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _marcar_entradas_con_numero_de_pagina(lineas: list[list[str]], quitar: list[set[int]]) -> None:
    """Corridas de entradas «Título - 12 -», aunque crucen páginas, y su encabezado."""
    llenas = [(n, i) for n, pagina in enumerate(lineas) for i, linea in enumerate(pagina) if linea.strip()]

    def con_numero(k: int) -> bool:
        n, i = llenas[k]
        return bool(_CON_NUMERO_DE_PAGINA.search(lineas[n][i]))

    k = 0
    while k < len(llenas):
        fin = k
        while fin < len(llenas) and con_numero(fin):
            fin += 1
        if fin - k >= MIN_ENTRADAS:
            for n, i in llenas[k:fin]:
                quitar[n].add(i)
            if k > 0:
                n, i = llenas[k - 1]
                if es_encabezado_de_indice(lineas[n][i]):
                    quitar[n].add(i)
        k = max(fin, k + 1)


def _marcar_esquema_anunciado(lineas: list[list[str]], quitar: list[set[int]]) -> None:
    """Índice sin números de página: lo anuncia un encabezado y sigue mientras todo sea esquema."""
    en_el_indice = False
    for n, pagina in enumerate(lineas):
        llenas = [i for i, linea in enumerate(pagina) if linea.strip() and i not in quitar[n]]
        if en_el_indice:
            entradas = [i for i in llenas if _ENTRADA_DE_ESQUEMA.match(pagina[i])]
            if llenas and len(entradas) >= _PROPORCION_EN_LAS_SIGUIENTES * len(llenas):
                quitar[n].update(entradas)
                continue
            en_el_indice = False
        for posicion, i in enumerate(llenas):
            if not es_encabezado_de_indice(pagina[i]):
                continue
            siguientes = llenas[posicion + 1 :]
            entradas = [j for j in siguientes if _ENTRADA_DE_ESQUEMA.match(pagina[j])]
            if len(entradas) >= MIN_ENTRADAS and len(entradas) >= _PROPORCION_EN_LA_PRIMERA_PAGINA * len(siguientes):
                quitar[n].update([i, *entradas])
                en_el_indice = True
            break
