"""
NuevaMente — División del documento en chunks, con la página de cada uno.

  - Tamaño y solapamiento en CARACTERES (CHUNK_SIZE=1000, CHUNK_OVERLAP=150),
    medidos con len(). No usa tiktoken, que descarga su vocabulario la primera
    vez y falla con la guardia de red activa.
  - Las páginas se normalizan por separado y se unen con "\\n\\n". Como se sabe
    dónde empieza cada una, cada chunk conoce su página de inicio y de fin. El
    divisor prefiere cortar en las líneas en blanco: una página más larga que
    CHUNK_SIZE se divide sola, y varias páginas cortas pueden quedar juntas en
    un mismo chunk (ahí `pagina_fin` es mayor que `pagina`).
  - Un texto suelto (por ejemplo, el `texto_extraido` del MCP, que ya viene con
    las páginas unidas) se divide igual, pero sus chunks quedan sin página.
  - `chunk_id` corto y estable dentro del documento (c0001, c0002...).
  - Los chunks de menos de CHUNK_FUSION caracteres se unen a un vecino: al
    anterior o, si empiezan con un título numerado («12 Qué evitar»), al
    siguiente, que es su sección. La unión es el texto de la fuente, sin
    repetir el solapamiento, y no pasa de CHUNK_SIZE + CHUNK_FUSION. Por
    cortos, esos fragmentos se parecían a cualquier consulta.
  - Los que igual quedan por debajo de CHUNK_MINIMO (una portada sola, un
    título suelto) no se indexan.
  - La tabla de contenido se quita antes de dividir (tabla_de_contenido.py):
    sus chunks no respondían consultas del tema y atraían consultas ajenas.
"""

from __future__ import annotations

import bisect
import re
from collections.abc import Sequence

from . import errores as e
from .configuracion import ConfigRAG, cargar_config
from .errores import ErrorRAG
from .extraccion import SEPARADOR_PAGINAS
from .modelos import Chunk, formatear_chunk_id
from .normalizador import normalizar, normalizar_por_pagina
from .tabla_de_contenido import quitar_tabla_de_contenido

def dividir_en_chunks(
    fuente: str | Sequence[str],
    document_id: str,
    config: ConfigRAG | None = None,
    *,
    normalizar_texto: bool = True,
) -> list[Chunk]:
    """
    Normaliza y divide el documento.

    `fuente` es una lista de páginas (lo recomendado: conserva la página) o un
    texto suelto. Con `normalizar_texto=False` no se normaliza, pero la tabla
    de contenido se quita igual.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # import diferido

    cfg = config if config is not None else cargar_config()
    con_paginas = not isinstance(fuente, str)

    if con_paginas:
        paginas = list(fuente)
        if normalizar_texto:
            paginas = normalizar_por_pagina(paginas)
    else:
        paginas = [normalizar(fuente) if normalizar_texto else fuente]
    paginas = quitar_tabla_de_contenido(paginas)

    texto, inicios = _unir_paginas(paginas)
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
        length_function=len,
        strip_whitespace=True,
    )

    tramos: list[list[int]] = []
    ultimo_inicio, ultimo_fin = -1, 0
    for contenido in divisor.split_text(texto):
        inicio = _ubicar(texto, contenido, max(ultimo_inicio + 1, ultimo_fin - cfg.chunk_overlap))
        ultimo_inicio, ultimo_fin = inicio, inicio + len(contenido)
        tramos.append([inicio, ultimo_fin])

    chunks: list[Chunk] = []
    for inicio, fin in _unir_cortos(texto, tramos, cfg):
        contenido = texto[inicio:fin]
        if len(contenido.strip()) < cfg.chunk_minimo:
            continue
        chunks.append(
            Chunk(
                chunk_id=formatear_chunk_id(len(chunks)),
                document_id=document_id,
                texto=contenido,
                orden=len(chunks),
                inicio=inicio,
                pagina=_pagina_de(inicio, inicios) if con_paginas else None,
                pagina_fin=_pagina_de(fin - 1, inicios) if con_paginas else None,
            )
        )
    return chunks


_TITULO_NUMERADO = re.compile(r"^\d+(?:\.\d+)*\.?\s+\S")


def _unir_cortos(texto: str, tramos: list[list[int]], cfg: ConfigRAG) -> list[list[int]]:
    """
    Une cada tramo de menos de CHUNK_FUSION caracteres a un vecino.

    Los tramos son [inicio, fin) dentro del texto unido, así que la unión es el
    texto de la fuente entre los dos, sin repetir el solapamiento. Se prefiere
    el tramo anterior; si el corto empieza con un título numerado, el siguiente.
    Si con el preferido se pasa de CHUNK_SIZE + CHUNK_FUSION, se prueba con el
    otro, y si tampoco cabe, queda como está.
    """
    if cfg.chunk_fusion <= 0:
        return tramos
    tope = cfg.chunk_size + cfg.chunk_fusion
    i = 0
    while i < len(tramos):
        inicio, fin = tramos[i]
        if fin - inicio >= cfg.chunk_fusion:
            i += 1
            continue
        vecinos = (i + 1, i - 1) if _TITULO_NUMERADO.match(texto[inicio:fin]) else (i - 1, i + 1)
        for j in vecinos:
            if not 0 <= j < len(tramos):
                continue
            a, b = min(i, j), max(i, j)
            union = [tramos[a][0], max(tramos[a][1], tramos[b][1])]
            entre = texto[tramos[a][1] : tramos[b][0]]
            if union[1] - union[0] <= tope and not entre.strip():
                tramos[a : b + 1] = [union]
                i = a  # el tramo unido se vuelve a mirar: puede seguir siendo corto
                break
        else:
            i += 1
    return tramos


def _unir_paginas(paginas: Sequence[str]) -> tuple[str, list[int]]:
    """
    Une las páginas y devuelve dónde empieza cada una dentro del texto unido.

    Las páginas vacías (las del índice, una vez quitado) no suman separadores:
    empiezan donde empieza la siguiente.
    """
    partes: list[str] = []
    inicios: list[int] = []
    posicion = 0
    for pagina in paginas:
        inicios.append(posicion)
        if pagina.strip():
            partes.append(pagina)
            posicion += len(pagina) + len(SEPARADOR_PAGINAS)
    return SEPARADOR_PAGINAS.join(partes), inicios


def _ubicar(texto: str, contenido: str, desde: int) -> int:
    """
    Posición del chunk en el texto unido, buscando desde `desde`.

    El que llama pasa el mayor entre el inicio del chunk anterior + 1 y su fin
    menos CHUNK_OVERLAP: el divisor nunca solapa más que eso. Así, un chunk
    corto que también aparece dentro del anterior se ubica donde lo cortó.
    """
    inicio = texto.find(contenido, desde)
    if inicio < 0:
        inicio = texto.find(contenido)
    if inicio < 0:  # no debería pasar: el divisor solo recorta espacios en los extremos
        raise ErrorRAG(
            "No se pudo preparar el documento para la búsqueda.",
            codigo=e.RAG_INDICE,
            detalle="Un chunk no aparece en el texto normalizado.",
        )
    return inicio


def _pagina_de(posicion: int, inicios: list[int]) -> int:
    """Número de página (desde 1) que contiene esa posición del texto unido."""
    return bisect.bisect_right(inicios, posicion)
