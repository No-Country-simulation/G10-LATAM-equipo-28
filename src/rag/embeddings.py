"""
NuevaMente — Embeddings e5 por la API de Hugging Face (T2-06, D-09).

POR QUÉ UNA CLASE PROPIA Y NO `HuggingFaceEndpointEmbeddings` TAL CUAL
---------------------------------------------------------------------
Revisado su código en langchain-huggingface 1.2.2:

  1. Manda todos los textos en UNA sola petición: un documento de cientos de
     chunks saldría en una petición gigante.
  2. Crea el cliente sin timeout: una petición colgada bloquea el grafo.
  3. No fija el proveedor y deja que `huggingface_hub` elija uno.

`EmbeddingsE5` hace la misma llamada (`InferenceClient.feature_extraction`),
pero con lotes, prefijos, timeout, reintentos y vectores normalizados, y cumple
la interfaz `Embeddings` de LangChain.

PREFIJOS DE e5
--------------
El modelo se entrenó con prefijos y sin ellos rinde peor:

  - "passage: " para lo que se indexa (chunks)          -> embed_documents()
  - "query: "   para lo que se busca (consultas, y las   -> embed_query(),
                afirmaciones que verifica fidelidad/)       embeder_consultas()

OJO CON LOS PUNTAJES
--------------------
Según la ficha del modelo, la similitud coseno de e5 se concentra entre 0,7 y
1,0 porque se entrenó con temperatura 0,01. Importa el orden, no el valor
absoluto: UMBRAL_RETRIEVAL y las bandas de fidelidad se calibran con datos
reales. La prueba en vivo de T2-06 (scripts/probar_embeddings_api.py) lo mide.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Protocol

import numpy as np
from langchain_core.embeddings import Embeddings

from . import errores as e
from .configuracion import ConfigRAG, cargar_config
from .errores import ErrorEmbeddings

logger = logging.getLogger(__name__)

PREFIJO_DOCUMENTO = "passage: "
PREFIJO_CONSULTA = "query: "

#: Tope de espera entre reintentos, aunque el servidor pida más con Retry-After.
ESPERA_MAXIMA_SEGUNDOS = 30.0

_REINTENTABLES = frozenset(
    {e.EMBEDDINGS_LIMITE, e.EMBEDDINGS_NO_DISPONIBLE, e.EMBEDDINGS_TIEMPO_AGOTADO}
)
_PATRON_TOKEN = re.compile(r"hf_[A-Za-z0-9]{6,}")


class ClienteFeatureExtraction(Protocol):
    """Lo único que se usa de `huggingface_hub.InferenceClient`."""

    def feature_extraction(self, text: str | list[str], **kwargs: Any) -> Any: ...


@dataclass
class EstadisticasEmbeddings:
    """Contadores de consumo y latencia. Sirven para estimar la cuota (T2-06)."""

    peticiones: int = 0
    peticiones_fallidas: int = 0
    reintentos: int = 0
    textos: int = 0
    caracteres: int = 0
    segundos: float = 0.0
    norma_cruda_min: float | None = None
    norma_cruda_max: float | None = None

    def registrar_normas(self, normas: np.ndarray) -> None:
        """Guarda el rango de normas de los vectores tal como llegan de la API."""
        minimo, maximo = float(normas.min()), float(normas.max())
        if self.norma_cruda_min is None or minimo < self.norma_cruda_min:
            self.norma_cruda_min = minimo
        if self.norma_cruda_max is None or maximo > self.norma_cruda_max:
            self.norma_cruda_max = maximo

    def como_dict(self) -> dict[str, Any]:
        return asdict(self)


def preparar_texto(texto: str, prefijo: str) -> str:
    """
    Deja un texto listo para e5: espacios simples y el prefijo una sola vez.

    Los saltos de línea se vuelven espacios, igual que en
    HuggingFaceEndpointEmbeddings.
    """
    limpio = " ".join(texto.split())
    if prefijo and limpio.startswith(prefijo):
        return limpio
    return f"{prefijo}{limpio}"


def dividir_en_lotes(textos: Sequence[str], tamano: int) -> Iterator[list[str]]:
    """Parte la lista en lotes de `tamano` textos, sin cambiar el orden."""
    if tamano < 1:
        raise ValueError("el tamaño de lote debe ser al menos 1")
    for inicio in range(0, len(textos), tamano):
        yield list(textos[inicio : inicio + tamano])


class EmbeddingsE5(Embeddings):
    """
    Embeddings de `intfloat/multilingual-e5-base` por la API de Hugging Face.

        emb = EmbeddingsE5()                          # lee el .env
        vectores = emb.embed_documents(chunks)        # "passage: ", en lotes
        consulta = emb.embed_query("Scrum Master")    # "query: "

    Los vectores salen normalizados (norma 1), así que el coseno es el producto
    punto. El cliente se crea en la primera llamada: construir la clase no
    falla aunque falte el token.

    `parametros_api` pasa parámetros extra a `feature_extraction` (por ejemplo,
    `{"truncate": True}`); la prueba en vivo dice cuáles acepta el proveedor.
    """

    def __init__(
        self,
        config: ConfigRAG | None = None,
        *,
        cliente: ClienteFeatureExtraction | None = None,
        parametros_api: dict[str, Any] | None = None,
        espera: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config if config is not None else cargar_config()
        self.parametros_api = dict(parametros_api or {})
        self.estadisticas = EstadisticasEmbeddings()
        self._cliente = cliente
        self._espera = espera

    def __repr__(self) -> str:
        return (
            f"EmbeddingsE5(modelo={self.config.modelo_embeddings!r}, "
            f"proveedor={self.config.proveedor_embeddings!r}, lote={self.config.tamano_lote})"
        )

    # ------------------------------------------------------------------
    # Interfaz de LangChain
    # ------------------------------------------------------------------

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Chunks para indexar: prefijo "passage: "."""
        return self.embeber(texts, PREFIJO_DOCUMENTO)

    def embed_query(self, text: str) -> list[float]:
        """Una consulta: prefijo "query: "."""
        return self.embeber([text], PREFIJO_CONSULTA)[0]

    # ------------------------------------------------------------------
    # API del RAG
    # ------------------------------------------------------------------

    def embeder_consultas(self, textos: Sequence[str]) -> list[list[float]]:
        """Varias consultas o afirmaciones a verificar, en lotes: prefijo "query: "."""
        return self.embeber(textos, PREFIJO_CONSULTA)

    def embeber(self, textos: Sequence[str], prefijo: str) -> list[list[float]]:
        """
        Nivel bajo: aplica `prefijo` (puede ser "") y manda los textos en lotes.

        Devuelve un vector normalizado por texto, en el mismo orden.
        """
        if isinstance(textos, str):
            raise TypeError("se esperaba una lista de textos, no un texto suelto")

        preparados: list[str] = []
        for posicion, texto in enumerate(textos):
            if not isinstance(texto, str) or not texto.strip():
                raise ErrorEmbeddings(
                    "No se puede calcular el embedding de un texto vacío.",
                    codigo=e.EMBEDDINGS_ENTRADA_INVALIDA,
                    detalle=f"El texto de la posición {posicion} está vacío o no es texto.",
                )
            preparados.append(preparar_texto(texto, prefijo))

        vectores: list[list[float]] = []
        for lote in dividir_en_lotes(preparados, self.config.tamano_lote):
            vectores.extend(self._embeber_lote(lote))
        return vectores

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _obtener_cliente(self) -> ClienteFeatureExtraction:
        if self._cliente is None:
            if not self.config.tiene_token:
                raise ErrorEmbeddings(
                    "Falta configurar el acceso al servicio de embeddings.",
                    codigo=e.EMBEDDINGS_SIN_TOKEN,
                    detalle=(
                        "Define HF_TOKEN en el .env de la raíz del repo (token fine-grained "
                        "con el permiso «Make calls to Inference Providers»)."
                    ),
                )
            # Import diferido: huggingface_hub pesa y las pruebas no lo necesitan.
            from huggingface_hub import InferenceClient

            self._cliente = InferenceClient(
                model=self.config.modelo_embeddings,
                provider=self.config.proveedor_embeddings,
                token=self.config.hf_token,
                timeout=self.config.timeout_segundos,
            )
        return self._cliente

    def _embeber_lote(self, lote: list[str]) -> list[list[float]]:
        cliente = self._obtener_cliente()
        intentos = self.config.reintentos + 1

        for intento in range(1, intentos + 1):
            inicio = time.perf_counter()
            try:
                respuesta = cliente.feature_extraction(lote, **self.parametros_api)
            except Exception as exc:  # noqa: BLE001 — se clasifica y se traduce abajo
                self._contar_peticion(inicio, fallida=True)
                error = self._traducir(exc)
                if error.codigo in _REINTENTABLES and intento < intentos:
                    segundos = self._segundos_de_espera(intento, exc)
                    self.estadisticas.reintentos += 1
                    logger.warning(
                        "Embeddings: falló el intento %d de %d (%s); reintento en %.1f s.",
                        intento,
                        intentos,
                        error.codigo,
                        segundos,
                    )
                    self._espera(segundos)
                    continue
                raise error from exc

            self._contar_peticion(inicio, fallida=False)
            vectores = self._a_vectores(respuesta, len(lote))
            self.estadisticas.textos += len(lote)
            self.estadisticas.caracteres += sum(len(t) for t in lote)
            return vectores

        raise AssertionError("inalcanzable: el ciclo siempre devuelve o lanza")

    def _contar_peticion(self, inicio: float, *, fallida: bool) -> None:
        self.estadisticas.peticiones += 1
        if fallida:
            self.estadisticas.peticiones_fallidas += 1
        self.estadisticas.segundos += time.perf_counter() - inicio

    @staticmethod
    def _segundos_de_espera(intento: int, exc: Exception) -> float:
        """Respeta Retry-After si viene; si no, espera 1, 2, 4... segundos."""
        pedido = _retry_after(exc)
        base = pedido if pedido is not None else float(2 ** (intento - 1))
        return min(base, ESPERA_MAXIMA_SEGUNDOS)

    def _a_vectores(self, respuesta: Any, esperados: int) -> list[list[float]]:
        try:
            matriz = np.asarray(respuesta, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise self._respuesta_invalida(
                f"No se pudo leer la respuesta como números ({type(respuesta).__name__})."
            ) from exc

        if matriz.ndim == 1 and esperados == 1:
            matriz = matriz.reshape(1, -1)
        if matriz.ndim != 2 or matriz.shape[0] != esperados:
            raise self._respuesta_invalida(
                f"Se esperaban {esperados} vectores y llegó un arreglo de forma {matriz.shape}. "
                "Con 3 dimensiones, la API devolvió un vector por token y no uno por texto."
            )
        if matriz.shape[1] != self.config.dimension_embeddings:
            raise self._respuesta_invalida(
                f"Los vectores tienen dimensión {matriz.shape[1]} y se esperaba "
                f"{self.config.dimension_embeddings} (EMBEDDINGS_DIMENSION)."
            )
        if not np.isfinite(matriz).all():
            raise self._respuesta_invalida("La respuesta trae valores no numéricos (NaN o infinito).")

        normas = np.linalg.norm(matriz, axis=1)
        self.estadisticas.registrar_normas(normas)
        if (normas == 0).any():
            raise self._respuesta_invalida("La respuesta trae un vector nulo.")
        return (matriz / normas[:, np.newaxis]).tolist()

    @staticmethod
    def _respuesta_invalida(detalle: str) -> ErrorEmbeddings:
        return ErrorEmbeddings(
            "El servicio de embeddings devolvió una respuesta inesperada.",
            codigo=e.EMBEDDINGS_RESPUESTA_INVALIDA,
            detalle=detalle,
        )

    def _sin_secretos(self, texto: str) -> str:
        if self.config.hf_token:
            texto = texto.replace(self.config.hf_token, "***")
        return _PATRON_TOKEN.sub("hf_***", texto)

    def _traducir(self, exc: Exception) -> ErrorEmbeddings:
        """Convierte cualquier falla del cliente en un `ErrorEmbeddings` sin claves."""
        estado = _codigo_http(exc)
        tecnico = self._sin_secretos(f"{type(exc).__name__}: {exc}")[:400]

        if estado in (401, 403):
            return ErrorEmbeddings(
                "El servicio de embeddings rechazó las credenciales.",
                codigo=e.EMBEDDINGS_TOKEN_INVALIDO,
                detalle=(
                    f"HTTP {estado}. Revisa que HF_TOKEN sea válido y tenga el permiso "
                    f"«Make calls to Inference Providers». {tecnico}"
                ),
            )
        if estado == 402:
            return ErrorEmbeddings(
                "Se agotó la cuota del servicio de embeddings.",
                codigo=e.EMBEDDINGS_SIN_CREDITOS,
                detalle=f"HTTP 402: se acabaron los créditos del mes en Hugging Face. {tecnico}",
            )
        if estado == 404:
            return ErrorEmbeddings(
                "El modelo de embeddings no está disponible.",
                codigo=e.EMBEDDINGS_MODELO_NO_ENCONTRADO,
                detalle=(
                    f"HTTP 404. Revisa EMBEDDINGS_MODELO ({self.config.modelo_embeddings}) y "
                    f"EMBEDDINGS_PROVEEDOR ({self.config.proveedor_embeddings}). {tecnico}"
                ),
            )
        if estado in (400, 413, 422):
            return ErrorEmbeddings(
                "El servicio de embeddings rechazó el texto enviado.",
                codigo=e.EMBEDDINGS_ENTRADA_INVALIDA,
                detalle=(
                    f"HTTP {estado}: puede ser un lote demasiado grande "
                    f"(EMBEDDINGS_LOTE={self.config.tamano_lote}) o un texto demasiado largo. {tecnico}"
                ),
            )
        if estado == 429:
            return ErrorEmbeddings(
                "El servicio de embeddings está limitando las peticiones; "
                "intenta de nuevo en unos minutos.",
                codigo=e.EMBEDDINGS_LIMITE,
                detalle=f"HTTP 429. {tecnico}",
            )
        if estado is not None and estado >= 500:
            return ErrorEmbeddings(
                "El servicio de embeddings no está disponible en este momento.",
                codigo=e.EMBEDDINGS_NO_DISPONIBLE,
                detalle=f"HTTP {estado}. {tecnico}",
            )
        if isinstance(exc, TimeoutError):
            return ErrorEmbeddings(
                "El servicio de embeddings tardó demasiado en responder.",
                codigo=e.EMBEDDINGS_TIEMPO_AGOTADO,
                detalle=(
                    f"Más de {self.config.timeout_segundos:g} s por petición "
                    f"(EMBEDDINGS_TIMEOUT). {tecnico}"
                ),
            )
        if _es_error_de_red(exc):
            return ErrorEmbeddings(
                "El servicio de embeddings no está disponible en este momento.",
                codigo=e.EMBEDDINGS_NO_DISPONIBLE,
                detalle=f"Falla de red o de proxy. {tecnico}",
            )
        return ErrorEmbeddings(
            "No se pudieron calcular los embeddings.",
            codigo=e.EMBEDDINGS_ERROR,
            detalle=tecnico,
        )


# =============================================================================
# Ayudas para clasificar errores
# =============================================================================


def _codigo_http(exc: Exception) -> int | None:
    """Código HTTP de un error de huggingface_hub (o de uno que se le parezca)."""
    estado = getattr(getattr(exc, "response", None), "status_code", None)
    return estado if isinstance(estado, int) else None


def _retry_after(exc: Exception) -> float | None:
    """Segundos que pide el servidor en la cabecera Retry-After, si los pide."""
    cabeceras = getattr(getattr(exc, "response", None), "headers", None)
    if not cabeceras:
        return None
    try:
        valor = cabeceras.get("Retry-After")
    except AttributeError:
        return None
    try:
        return max(0.0, float(valor)) if valor is not None else None
    except (TypeError, ValueError):
        return None  # Retry-After también puede venir como fecha; ahí se usa la espera normal


def _es_error_de_red(exc: Exception) -> bool:
    if isinstance(exc, ConnectionError):
        return True
    try:
        import httpx
    except ImportError:
        return False
    return isinstance(exc, httpx.TransportError)
