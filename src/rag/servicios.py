"""
NuevaMente — Instancias compartidas del RAG (una por proceso).

El grafo llama a `indexar_documento()` y a `recuperar()` muchas veces: crear
en cada llamada el cliente de Hugging Face y el de Chroma sería lento. Estas
funciones los crean la primera vez, con la configuración del .env, y después
los reutilizan.

Las pruebas no las usan: pasan sus propias instancias. Si cambias el .env con
el proceso en marcha, llama a `reiniciar()`.
"""

from __future__ import annotations

from functools import lru_cache

from .configuracion import ConfigRAG, cargar_config
from .embeddings import EmbeddingsE5
from .vectorstore import AlmacenChroma


@lru_cache(maxsize=1)
def config_por_defecto() -> ConfigRAG:
    return cargar_config()


@lru_cache(maxsize=1)
def embeddings_por_defecto() -> EmbeddingsE5:
    return EmbeddingsE5(config_por_defecto())


@lru_cache(maxsize=1)
def almacen_por_defecto() -> AlmacenChroma:
    return AlmacenChroma(config_por_defecto())


def reiniciar() -> None:
    """Olvida las instancias creadas: la próxima llamada relee el .env."""
    config_por_defecto.cache_clear()
    embeddings_por_defecto.cache_clear()
    almacen_por_defecto.cache_clear()
