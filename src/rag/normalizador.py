"""
NuevaMente — Normalizacion del texto extraido.

POR QUE EXISTE ESTE ARCHIVO
---------------------------
No es precaucion teorica. Se confirmo sobre los 5 PDFs reales de prueba
(guias de europeanscrum.org). Muestra literal de lo que devuelve la extraccion:

    - 4 - 5 Resp onsabilidades Integral es del Scrum Maste r
    ¥ Con el Product Owner: ayuda a mantener un Backlog ordenado, gestionar ex pectativas

Cuatro defectos, todos presentes:

  1. Espacios DENTRO de las palabras  ("Resp onsabilidades", "Maste r")
     Es el mas grave: degrada los embeddings y el LLM reproduce el texto roto.
  2. Vinetas corruptas  ("¥" en vez de "•")
  3. Encabezados y numeros de pagina pegados a los titulos
  4. Paginas sin texto extraible

Si esto no se corrige ANTES del chunking, el defecto se propaga a los chunks,
a los embeddings, a la recuperacion y al puntaje de fidelidad. Limpiar despues
obliga a reindexar todo.

DISENO
------
Funciones puras sobre strings. Sin dependencias externas. Se prueban solas.
El pipeline es `normalizar()`; cada paso se puede usar por separado.
"""

from __future__ import annotations

import re
import unicodedata

# =============================================================================
# 1. Vinetas y caracteres sustituidos por la extraccion
# =============================================================================

#: Simbolos que los PDFs de prueba devuelven en lugar de vinetas.
#: "¥" aparece en las guias de europeanscrum.org; el resto son los sustitutos
#: mas frecuentes segun la fuente tipografica del documento.
_VINETAS = {
    "¥": "-",   # lo que devuelven las guias de europeanscrum.org
    "•": "-",
    "§": "-",
    "‣": "-",
    "▪": "-",
    "●": "-",
    "◦": "-",
}

_COMILLAS = {
    "“": '"', "”": '"', "‘": "'", "’": "'",
    "–": "-", "—": "-", "…": "...",
}


def limpiar_simbolos(texto: str) -> str:
    """Reemplaza vinetas corruptas y comillas tipograficas por ASCII."""
    for malo, bueno in {**_VINETAS, **_COMILLAS}.items():
        texto = texto.replace(malo, bueno)
    # Caracteres de control y espacios raros
    texto = texto.replace("\xa0", " ").replace("​", "")
    texto = "".join(c for c in texto if c == "\n" or not unicodedata.category(c).startswith("C"))
    return texto


# =============================================================================
# 2. El defecto grave: espacios dentro de las palabras
# =============================================================================

#: Palabras cortas legitimas del espanol que NO deben pegarse a la siguiente.
#: Sin esta lista, "de coracion" se une bien pero "de la casa" se rompe.
_PALABRAS_CORTAS_VALIDAS = frozenset(
    """a al ante bajo con contra de del desde durante en entre hacia hasta mediante
    para por segun sin so sobre tras y e o u ni que si no se le la lo las los les
    me te nos os su sus mi mis tu tus un una unos unas el ya es son fue ser han hay
    muy mas pero como cuando donde quien cual cuyo esta este esto estos estas ese esa
    eso esos esas aquel aquella da di ir va ve vi ha he ver dar uno dos tres
    cuatro cinco seis siete ocho nueve diez ante rol fin vez pie red uso
    ley tipo caso dato area nivel"""
    .split()
)


def unir_palabras_partidas(texto: str) -> str:
    """
    Repara los cortes que mete la extraccion de PDF dentro de las palabras.

    DOS REGLAS, las dos conservadoras. Ante la duda no toca nada: es preferible
    dejar un corte sin reparar que fusionar "de la" en "dela".

      Regla A — fragmento DERECHO de 1 o 2 letras que no es palabra valida.
                Un resto tan corto casi siempre es una palabra partida.
                    "Maste r"  -> "Master"
                    "quie n"   -> "quien"
                Se limito a 2 letras y no a 3 porque con 3 se unia
                "Contenido uno" -> "Contenidouno". Corromper texto correcto es
                peor que dejar un corte que ya venia roto.

      Regla B — fragmento IZQUIERDO de 2 a 4 letras que no es palabra valida,
                seguido de un fragmento largo.
                    "Resp onsabilidades" -> "Responsabilidades"
                    "ex pectativas"      -> "expectativas"

    Lo que NO toca, a proposito:
        "de la organizacion"  -> ambas son palabras validas
        "El Scrum Master"     -> "Master" empieza en mayuscula
        "scrum masters"       -> izquierda de 5 letras, derecha de 7: ninguna regla aplica
        "Integral es del"     -> "es" es palabra valida
        "sistemi cos"         -> resto de 3 letras; lo agarraria la regla A vieja, pero
                                 esa version rompia texto correcto

    Estos ultimos son el precio de no corromper texto bueno. Un corte sin
    reparar degrada un embedding; una fusion incorrecta inventa una palabra
    que no existe en el documento.
    """

    _LETRA = (
        "A-Za-z\u00c1\u00c9\u00cd\u00d3\u00da\u00dc\u00d1"
        "\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1"
    )
    _MINUS = "a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1"

    def _regla_b(m: re.Match[str]) -> str:
        """Prefijo corto que no es palabra + fragmento largo."""
        izq, der = m.group(1), m.group(2)
        if 2 <= len(izq) <= 4 and izq.lower() not in _PALABRAS_CORTAS_VALIDAS:
            return izq + der
        return m.group(0)

    def _regla_a(m: re.Match[str]) -> str:
        """Palabra truncada + resto de 1-2 letras que no es palabra."""
        izq, der = m.group(1), m.group(2)
        if der.lower() in _PALABRAS_CORTAS_VALIDAS:
            return m.group(0)
        # Si la izquierda es larga, probablemente es una palabra COMPLETA y el
        # corte esta en otro lado. Sin esta guarda, "gestionar ex pectativas"
        # se convertia en "gestionarex pectativas".
        if len(izq) > 6:
            return m.group(0)
        return izq + der

    patron_b = re.compile(rf"\b([{_LETRA}]{{2,4}}) ([{_MINUS}]{{4,}})\b")
    patron_a = re.compile(rf"\b([{_LETRA}]{{2,6}}) ([{_MINUS}]{{1,2}})\b")

    # ORDEN IMPORTANTE: primero B, despues A.
    # Si A corre primero, en "gestionar ex pectativas" se come el "ex" con la
    # palabra anterior y deja "pectativas" huerfano.
    anterior = None
    while anterior != texto:
        anterior = texto
        texto = patron_b.sub(_regla_b, texto)

    anterior = None
    while anterior != texto:
        anterior = texto
        texto = patron_a.sub(_regla_a, texto)

    return texto


def unir_guiones_de_corte(texto: str) -> str:
    """Repara el corte de palabra a final de linea: "organi-\\nzacion"."""
    return re.sub(r"([a-záéíóúüñ])-\s*\n\s*([a-záéíóúüñ])", r"\1\2", texto)


# =============================================================================
# 3. Ruido de encabezado y pie
# =============================================================================

_RUIDO = (
    re.compile(r"^\s*-?\s*\d{1,3}\s*-?\s*$"),          # "- 4 -", "12"
    re.compile(r"^\s*p[aá]g(ina)?\.?\s*\d+.*$", re.I),  # "Pagina 4 de 20"
    re.compile(r"^\s*www\.[^\s]+\s*$", re.I),           # "www.europeanscrum.org"
    re.compile(r"^\s*https?://\S+\s*$", re.I),
    re.compile(r"^\s*[-_=·.]{3,}\s*$"),                 # separadores
)


def quitar_ruido_de_linea(texto: str) -> str:
    """Elimina lineas que son sólo encabezado, pie o numero de pagina."""
    return "\n".join(l for l in texto.split("\n") if not any(p.match(l) for p in _RUIDO))


def separar_numero_de_pagina_pegado(texto: str) -> str:
    """
    Repara "- 4 - 5 Responsabilidades" -> "5 Responsabilidades".

    Pasa cuando el pie de pagina queda en la misma linea que el titulo.
    """
    return re.sub(r"^\s*-\s*\d{1,3}\s*-\s*", "", texto, flags=re.M)


def quitar_encabezado_repetido(paginas: list[str], umbral: float = 0.6) -> list[str]:
    """
    Detecta y elimina las lineas que se repiten en la mayoria de las paginas.

    Es la forma robusta de sacar encabezados y pies: en vez de adivinar el
    formato, se apoya en que se repiten. Necesita el texto POR PAGINA, no el
    documento entero concatenado.
    """
    if len(paginas) < 3:
        return paginas

    conteo: dict[str, int] = {}
    for p in paginas:
        for l in {x.strip() for x in p.split("\n")[:3] + p.split("\n")[-3:] if x.strip()}:
            conteo[l] = conteo.get(l, 0) + 1

    minimo = max(2, int(len(paginas) * umbral))
    repetidas = {l for l, n in conteo.items() if n >= minimo and len(l) < 120}

    return [
        "\n".join(l for l in p.split("\n") if l.strip() not in repetidas) for p in paginas
    ]


# =============================================================================
# 4. Espaciado
# =============================================================================


def quitar_puntos_guia(texto: str) -> str:
    """
    Colapsa los puntos guia del indice: "Sprint Planning ......... - 4 -".

    Sin esto, la pagina de indice produce chunks que son casi puros puntos:
    ruido puro para los embeddings.
    """
    texto = re.sub(r"[.\u00b7]{4,}", " ", texto)
    return re.sub(r"(?:\s*\.\s*){4,}", " ", texto)


def normalizar_espacios(texto: str) -> str:
    """Colapsa espacios repetidos y limita los saltos de linea a dos."""
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r" *\n *", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


# =============================================================================
# 5. El pipeline
# =============================================================================


def normalizar(texto: str) -> str:
    """
    Normaliza texto ya concatenado.

    Si tienes el texto POR PAGINA, usa `normalizar_paginas()`: detecta mejor los
    encabezados repetidos.
    """
    texto = limpiar_simbolos(texto)
    texto = unir_guiones_de_corte(texto)
    texto = separar_numero_de_pagina_pegado(texto)
    texto = quitar_ruido_de_linea(texto)
    texto = quitar_puntos_guia(texto)
    texto = unir_palabras_partidas(texto)
    return normalizar_espacios(texto)


def normalizar_paginas(paginas: list[str]) -> str:
    """
    Normaliza una lista de paginas y las une. Es la via recomendada:
    permite detectar encabezados y pies por repeticion entre paginas.

        from pypdf import PdfReader
        paginas = [(p.extract_text() or "") for p in PdfReader(ruta).pages]
        texto = normalizar_paginas(paginas)
    """
    paginas = [limpiar_simbolos(p) for p in paginas]
    paginas = quitar_encabezado_repetido(paginas)
    return normalizar("\n\n".join(paginas))


# =============================================================================
# Diagnostico:  python src/rag/normalizador.py <archivo.pdf>
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("uso: python src/rag/normalizador.py <archivo.pdf>")
        raise SystemExit(1)

    from pypdf import PdfReader  # import local: solo el diagnostico lo necesita

    paginas = [(p.extract_text() or "") for p in PdfReader(sys.argv[1]).pages]
    crudo = "\n\n".join(paginas)
    limpio = normalizar_paginas(paginas)

    print(f"  crudo:  {len(crudo):>7,} chars")
    print(f"  limpio: {len(limpio):>7,} chars  ({len(crudo) - len(limpio):+,})\n")
    print("--- ANTES ---")
    print(crudo[:500])
    print("\n--- DESPUES ---")
    print(limpio[:500])
