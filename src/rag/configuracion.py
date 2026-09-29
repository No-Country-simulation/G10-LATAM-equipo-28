"""
NuevaMente — Configuración del RAG.

Lee el `.env` de la raíz del repositorio y aplica los valores del plan. Es
independiente de `src/config.py` a propósito:

  - `src/config.py` de `main` solo acepta `EMBEDDINGS_PROVIDER` = ollama o
    gemini, y los embeddings del plan van por la API de Hugging Face (D-09).
  - `grafo.py` corre con `src/` como directorio de trabajo e importa por nombre
    (`rag`), mientras que las pruebas importan `src.rag`. Sin dependencias
    fuera de `src/rag/`, el paquete funciona de las dos formas.

Variables del .env. Todas son opcionales, salvo el token para usar la API:

    HF_TOKEN               Token de Hugging Face. También se acepta
                           HUGGINGFACEHUB_API_TOKEN. Nunca se imprime.
    EMBEDDINGS_MODELO      intfloat/multilingual-e5-base
    EMBEDDINGS_PROVEEDOR   hf-inference
    EMBEDDINGS_DIMENSION   768
    EMBEDDINGS_LOTE        32    textos por petición
    EMBEDDINGS_TIMEOUT     30    segundos por petición
    EMBEDDINGS_REINTENTOS  3     ante 429, 5xx, tiempo agotado o falla de red
    CHUNK_SIZE             1000  caracteres
    CHUNK_OVERLAP          150   caracteres
    RETRIEVAL_TOP_K        5
    UMBRAL_RETRIEVAL       0.78  (distinto de UMBRAL_FIDELIDAD, D-12)
    CHROMA_PATH            ./chroma_db; si es relativo, cuenta desde la raíz
                           del repo y no desde el directorio de trabajo

Los decimales aceptan punto o coma: 0.78 y 0,78 valen lo mismo.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .errores import ErrorConfiguracionRAG

#: Raíz del repositorio: src/rag/configuracion.py -> parents[2].
RAIZ_REPO = Path(__file__).resolve().parents[2]

MODELO_POR_DEFECTO = "intfloat/multilingual-e5-base"
PROVEEDOR_POR_DEFECTO = "hf-inference"
DIMENSION_E5_BASE = 768
CHROMA_PATH_POR_DEFECTO = "./chroma_db"

_MENSAJE_INVALIDA = "La configuración del RAG no es válida."


def resolver_ruta(valor: str | Path) -> Path:
    """Devuelve una ruta absoluta; si `valor` es relativo, cuenta desde la raíz del repo."""
    ruta = Path(valor).expanduser()
    if not ruta.is_absolute():
        ruta = RAIZ_REPO / ruta
    return ruta.resolve()


@dataclass(frozen=True)
class ConfigRAG:
    """Parámetros del RAG. Inmutable: para variar uno, usa `dataclasses.replace`."""

    hf_token: str | None = field(default=None, repr=False)
    modelo_embeddings: str = MODELO_POR_DEFECTO
    proveedor_embeddings: str = PROVEEDOR_POR_DEFECTO
    dimension_embeddings: int = DIMENSION_E5_BASE
    tamano_lote: int = 32
    timeout_segundos: float = 30.0
    reintentos: int = 3
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 5
    umbral_retrieval: float = 0.78
    chroma_path: Path = field(default_factory=lambda: resolver_ruta(CHROMA_PATH_POR_DEFECTO))

    def __post_init__(self) -> None:
        # La ruta se guarda siempre absoluta, aunque llegue como texto relativo.
        object.__setattr__(self, "chroma_path", resolver_ruta(self.chroma_path))
        self.validar()

    @property
    def tiene_token(self) -> bool:
        return bool(self.hf_token)

    def validar(self) -> None:
        """Lanza `ErrorConfiguracionRAG` con todos los problemas juntos."""
        problemas: list[str] = []
        if not self.modelo_embeddings.strip():
            problemas.append("EMBEDDINGS_MODELO no puede quedar vacío")
        if not self.proveedor_embeddings.strip():
            problemas.append("EMBEDDINGS_PROVEEDOR no puede quedar vacío")
        if self.dimension_embeddings < 1:
            problemas.append("EMBEDDINGS_DIMENSION debe ser mayor que 0")
        if self.tamano_lote < 1:
            problemas.append("EMBEDDINGS_LOTE debe ser al menos 1")
        if self.timeout_segundos <= 0:
            problemas.append("EMBEDDINGS_TIMEOUT debe ser mayor que 0")
        if self.reintentos < 0:
            problemas.append("EMBEDDINGS_REINTENTOS no puede ser negativo")
        if self.chunk_size < 1:
            problemas.append("CHUNK_SIZE debe ser mayor que 0")
        if not 0 <= self.chunk_overlap < self.chunk_size:
            problemas.append(
                f"CHUNK_OVERLAP ({self.chunk_overlap}) debe estar entre 0 y "
                f"CHUNK_SIZE ({self.chunk_size}), sin llegar a CHUNK_SIZE"
            )
        if self.top_k < 1:
            problemas.append("RETRIEVAL_TOP_K debe ser al menos 1")
        if not 0.0 < self.umbral_retrieval <= 1.0:
            problemas.append(
                f"UMBRAL_RETRIEVAL debe estar entre 0 y 1; vale {self.umbral_retrieval}"
            )
        if problemas:
            raise ErrorConfiguracionRAG(_MENSAJE_INVALIDA, detalle="; ".join(problemas) + ".")

    def resumen_seguro(self) -> str:
        """Resumen para la consola o los registros. Nunca incluye el token."""
        return (
            f"modelo={self.modelo_embeddings} · proveedor={self.proveedor_embeddings} · "
            f"lote={self.tamano_lote} · timeout={self.timeout_segundos:g}s · "
            f"reintentos={self.reintentos} · chunks={self.chunk_size}/{self.chunk_overlap} · "
            f"top_k={self.top_k} · umbral={self.umbral_retrieval} · "
            f"token={'presente' if self.tiene_token else 'AUSENTE'}"
        )


# =============================================================================
# Carga desde el entorno
# =============================================================================


def _texto(entorno: Mapping[str, str], nombre: str) -> str:
    return (entorno.get(nombre) or "").strip()


def _entero(entorno: Mapping[str, str], nombre: str, defecto: int) -> int:
    valor = _texto(entorno, nombre)
    if not valor:
        return defecto
    try:
        return int(valor)
    except ValueError:
        raise ErrorConfiguracionRAG(
            _MENSAJE_INVALIDA, detalle=f"{nombre} debe ser un número entero; llegó {valor!r}."
        ) from None


def _decimal(entorno: Mapping[str, str], nombre: str, defecto: float) -> float:
    valor = _texto(entorno, nombre)
    if not valor:
        return defecto
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        raise ErrorConfiguracionRAG(
            _MENSAJE_INVALIDA, detalle=f"{nombre} debe ser un número; llegó {valor!r}."
        ) from None


def _cargar_dotenv() -> None:
    """Carga el .env de la raíz del repo sin pisar variables ya definidas."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv está en requirements.txt; sin él, solo el entorno
        return
    load_dotenv(RAIZ_REPO / ".env", override=False)


def cargar_config(entorno: Mapping[str, str] | None = None, *, usar_dotenv: bool = True) -> ConfigRAG:
    """
    Arma la configuración del RAG.

    Sin argumentos, lee el `.env` de la raíz del repo y las variables de
    entorno. Con `entorno`, usa solo ese diccionario y no toca el `.env`:
    así las pruebas no dependen de la máquina.
    """
    if entorno is None:
        if usar_dotenv:
            _cargar_dotenv()
        entorno = os.environ

    token = _texto(entorno, "HF_TOKEN") or _texto(entorno, "HUGGINGFACEHUB_API_TOKEN")

    return ConfigRAG(
        hf_token=token or None,
        modelo_embeddings=_texto(entorno, "EMBEDDINGS_MODELO") or MODELO_POR_DEFECTO,
        proveedor_embeddings=_texto(entorno, "EMBEDDINGS_PROVEEDOR") or PROVEEDOR_POR_DEFECTO,
        dimension_embeddings=_entero(entorno, "EMBEDDINGS_DIMENSION", DIMENSION_E5_BASE),
        tamano_lote=_entero(entorno, "EMBEDDINGS_LOTE", 32),
        timeout_segundos=_decimal(entorno, "EMBEDDINGS_TIMEOUT", 30.0),
        reintentos=_entero(entorno, "EMBEDDINGS_REINTENTOS", 3),
        chunk_size=_entero(entorno, "CHUNK_SIZE", 1000),
        chunk_overlap=_entero(entorno, "CHUNK_OVERLAP", 150),
        top_k=_entero(entorno, "RETRIEVAL_TOP_K", 5),
        umbral_retrieval=_decimal(entorno, "UMBRAL_RETRIEVAL", 0.78),
        chroma_path=resolver_ruta(_texto(entorno, "CHROMA_PATH") or CHROMA_PATH_POR_DEFECTO),
    )
