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
  - Los chunks de menos de CHUNK_MINIMO caracteres (una portada, un título
    suelto) no se indexan: por cortos, se parecen a cualquier consulta.
"""

from __future__ import annotations

import bisect
from collections.abc import Sequence

from . import errores as e
from .configuracion import ConfigRAG, cargar_config
from .errores import ErrorRAG
from .extraccion import SEPARADOR_PAGINAS
from .modelos import Chunk, formatear_chunk_id
from .normalizador import normalizar, normalizar_por_pagina

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
    texto suelto. Con `normalizar_texto=False` se usa tal cual llega.
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

    texto, inicios = _unir_paginas(paginas)
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
        length_function=len,
        strip_whitespace=True,
    )

    chunks: list[Chunk] = []
    ultimo_inicio = -1
    for contenido in divisor.split_text(texto):
        inicio = _ubicar(texto, contenido, ultimo_inicio)
        ultimo_inicio = inicio
        if len(contenido.strip()) < cfg.chunk_minimo:
            continue
        fin = inicio + len(contenido) - 1
        chunks.append(
            Chunk(
                chunk_id=formatear_chunk_id(len(chunks)),
                document_id=document_id,
                texto=contenido,
                orden=len(chunks),
                inicio=inicio,
                pagina=_pagina_de(inicio, inicios) if con_paginas else None,
                pagina_fin=_pagina_de(fin, inicios) if con_paginas else None,
            )
        )
    return chunks


def _unir_paginas(paginas: Sequence[str]) -> tuple[str, list[int]]:
    """Une las páginas y devuelve dónde empieza cada una dentro del texto unido."""
    inicios: list[int] = []
    posicion = 0
    for pagina in paginas:
        inicios.append(posicion)
        posicion += len(pagina) + len(SEPARADOR_PAGINAS)
    return SEPARADOR_PAGINAS.join(paginas), inicios


def _ubicar(texto: str, contenido: str, ultimo_inicio: int) -> int:
    """Posición del chunk en el texto unido; siempre después del chunk anterior."""
    inicio = texto.find(contenido, ultimo_inicio + 1)
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
