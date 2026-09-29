"""
NuevaMente — Pruebas de EmbeddingsE5 (T2-06), sin red.

Un cliente falso reemplaza a `huggingface_hub.InferenceClient`: devuelve
vectores deterministas SIN normalizar y registra cada llamada. Así se prueban
los prefijos, los lotes, los reintentos y los errores sin gastar cuota.

La prueba contra la API real es `scripts/probar_embeddings_api.py`.

Ejecutar:  pytest tests/test_rag_embeddings.py -v
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest
from langchain_core.embeddings import Embeddings

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag import errores as e  # noqa: E402
from src.rag.configuracion import ConfigRAG  # noqa: E402
from src.rag.embeddings import (  # noqa: E402
    ESPERA_MAXIMA_SEGUNDOS,
    PREFIJO_CONSULTA,
    PREFIJO_DOCUMENTO,
    URL_HF_INFERENCE,
    EmbeddingsE5,
    dividir_en_lotes,
    preparar_texto,
    url_de_embeddings,
)
from src.rag.errores import ErrorEmbeddings  # noqa: E402

TOKEN = "hf_tokenDePrueba123456"
DIMENSION = 768


# =============================================================================
# Dobles de prueba
# =============================================================================


def vector_crudo(texto: str, dimension: int = DIMENSION) -> np.ndarray:
    """Vector determinista y sin normalizar (norma bastante mayor que 1)."""
    semilla = int(hashlib.sha256(texto.encode("utf-8")).hexdigest()[:8], 16)
    return np.random.default_rng(semilla).normal(size=dimension) * 3.0


class _Respuesta:
    def __init__(self, status_code: int, headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self.headers = headers or {}


class ErrorHTTPFalso(Exception):
    """Imita a HfHubHTTPError: trae `response.status_code` y `response.headers`."""

    def __init__(self, estado: int, mensaje: str = "", headers: dict[str, str] | None = None) -> None:
        super().__init__(mensaje or f"HTTP {estado}")
        self.response = _Respuesta(estado, headers)


class ClienteFalso:
    """Registra las llamadas; lanza las fallas programadas y después responde."""

    def __init__(self, *, fallas: list[Exception] | None = None, dimension: int = DIMENSION, respuesta=None):
        self.llamadas: list[list[str]] = []
        self.kwargs: list[dict] = []
        self.fallas = list(fallas or [])
        self.dimension = dimension
        self.respuesta = respuesta

    def feature_extraction(self, text, **kwargs):
        self.llamadas.append(list(text))
        self.kwargs.append(kwargs)
        if self.fallas:
            raise self.fallas.pop(0)
        if self.respuesta is not None:
            return self.respuesta
        return np.array([vector_crudo(t, self.dimension) for t in text])


def crear(cliente=None, *, espera=None, parametros_api=None, **config) -> EmbeddingsE5:
    config.setdefault("hf_token", TOKEN)
    return EmbeddingsE5(
        ConfigRAG(**config),
        cliente=cliente if cliente is not None else ClienteFalso(),
        espera=espera if espera is not None else (lambda s: None),
        parametros_api=parametros_api,
    )


# =============================================================================
# 1. Prefijos y preparación del texto
# =============================================================================


def test_documentos_llevan_prefijo_passage():
    cliente = ClienteFalso()
    crear(cliente).embed_documents(["El Scrum Master facilita.", "Otro chunk."])
    assert cliente.llamadas == [["passage: El Scrum Master facilita.", "passage: Otro chunk."]]


def test_consultas_llevan_prefijo_query():
    cliente = ClienteFalso()
    emb = crear(cliente)
    emb.embed_query("Scrum Master")
    emb.embeder_consultas(["¿Qué hace el Scrum Master?", "Product Owner"])
    assert cliente.llamadas == [
        ["query: Scrum Master"],
        ["query: ¿Qué hace el Scrum Master?", "query: Product Owner"],
    ]


def test_no_duplica_el_prefijo():
    assert preparar_texto("passage: ya viene", PREFIJO_DOCUMENTO) == "passage: ya viene"
    assert preparar_texto("query: ya viene", PREFIJO_CONSULTA) == "query: ya viene"


def test_saltos_de_linea_y_espacios_de_mas_se_vuelven_un_espacio():
    assert preparar_texto("  Sprint\nPlanning \n\n  y   Review ", "") == "Sprint Planning y Review"


def test_sin_prefijo_manda_el_texto_tal_cual():
    cliente = ClienteFalso()
    crear(cliente).embeber(["Scrum Master"], prefijo="")
    assert cliente.llamadas == [["Scrum Master"]]


# =============================================================================
# 2. Lotes y orden
# =============================================================================


def test_divide_en_lotes_de_32():
    cliente = ClienteFalso()
    textos = [f"chunk {i}" for i in range(70)]
    vectores = crear(cliente, tamano_lote=32).embed_documents(textos)
    assert [len(lote) for lote in cliente.llamadas] == [32, 32, 6]
    assert len(vectores) == 70


def test_respeta_el_tamano_de_lote_configurado():
    cliente = ClienteFalso()
    crear(cliente, tamano_lote=8).embed_documents([f"t{i}" for i in range(17)])
    assert [len(lote) for lote in cliente.llamadas] == [8, 8, 1]


def test_conserva_el_orden_de_los_textos():
    textos = [f"texto número {i}" for i in range(10)]
    vectores = np.array(crear(ClienteFalso(), tamano_lote=3).embed_documents(textos))
    for i, texto in enumerate(textos):
        esperado = vector_crudo(PREFIJO_DOCUMENTO + texto)
        esperado /= np.linalg.norm(esperado)
        assert np.allclose(vectores[i], esperado)


def test_dividir_en_lotes_rechaza_tamano_cero():
    with pytest.raises(ValueError):
        list(dividir_en_lotes(["a"], 0))


def test_lista_vacia_no_llama_a_la_api():
    cliente = ClienteFalso()
    assert crear(cliente).embed_documents([]) == []
    assert cliente.llamadas == []


# =============================================================================
# 3. Vectores
# =============================================================================


def test_los_vectores_salen_normalizados():
    emb = crear(ClienteFalso())
    vectores = np.array(emb.embed_documents(["uno", "dos", "tres"]))
    assert vectores.shape == (3, DIMENSION)
    assert np.allclose(np.linalg.norm(vectores, axis=1), 1.0)
    # La API (falsa) los manda sin normalizar: se registra la norma cruda.
    assert emb.estadisticas.norma_cruda_min > 1.0


def test_embed_query_devuelve_un_solo_vector():
    vector = crear(ClienteFalso()).embed_query("Scrum Master")
    assert isinstance(vector, list) and len(vector) == DIMENSION


def test_acepta_un_vector_plano_para_un_solo_texto():
    cliente = ClienteFalso(respuesta=vector_crudo("x"))
    assert len(crear(cliente).embed_query("x")) == DIMENSION


def test_rechaza_una_dimension_inesperada():
    with pytest.raises(ErrorEmbeddings) as info:
        crear(ClienteFalso(dimension=384)).embed_query("x")
    assert info.value.codigo == e.EMBEDDINGS_RESPUESTA_INVALIDA
    assert "384" in info.value.detalle


def test_rechaza_embeddings_por_token():
    por_token = np.ones((1, 7, DIMENSION))
    with pytest.raises(ErrorEmbeddings) as info:
        crear(ClienteFalso(respuesta=por_token)).embed_query("x")
    assert info.value.codigo == e.EMBEDDINGS_RESPUESTA_INVALIDA
    assert "por token" in info.value.detalle


def test_rechaza_cantidad_de_vectores_distinta_a_la_pedida():
    dos = np.ones((2, DIMENSION))
    with pytest.raises(ErrorEmbeddings) as info:
        crear(ClienteFalso(respuesta=dos)).embed_documents(["a", "b", "c"])
    assert info.value.codigo == e.EMBEDDINGS_RESPUESTA_INVALIDA


def test_rechaza_vectores_nulos_y_valores_no_numericos():
    for respuesta in (np.zeros((1, DIMENSION)), np.full((1, DIMENSION), np.nan)):
        with pytest.raises(ErrorEmbeddings) as info:
            crear(ClienteFalso(respuesta=respuesta)).embed_query("x")
        assert info.value.codigo == e.EMBEDDINGS_RESPUESTA_INVALIDA


# =============================================================================
# 4. Entradas inválidas
# =============================================================================


@pytest.mark.parametrize("vacio", ["", "   ", "\n\t"])
def test_texto_vacio_falla_y_dice_la_posicion(vacio):
    cliente = ClienteFalso()
    with pytest.raises(ErrorEmbeddings) as info:
        crear(cliente).embed_documents(["bien", vacio])
    assert info.value.codigo == e.EMBEDDINGS_ENTRADA_INVALIDA
    assert "posición 1" in info.value.detalle
    assert cliente.llamadas == []  # falla antes de gastar cuota


def test_texto_suelto_en_vez_de_lista_es_un_error_de_programacion():
    with pytest.raises(TypeError):
        crear(ClienteFalso()).embed_documents("un texto suelto")  # type: ignore[arg-type]


# =============================================================================
# 5. Reintentos
# =============================================================================


def test_reintenta_ante_503_y_termina_respondiendo():
    esperas: list[float] = []
    cliente = ClienteFalso(fallas=[ErrorHTTPFalso(503), ErrorHTTPFalso(503)])
    emb = crear(cliente, espera=esperas.append)
    assert len(emb.embed_query("x")) == DIMENSION
    assert esperas == [1.0, 2.0]
    assert len(cliente.llamadas) == 3
    assert emb.estadisticas.reintentos == 2
    assert emb.estadisticas.peticiones_fallidas == 2


def test_respeta_retry_after_en_429():
    esperas: list[float] = []
    cliente = ClienteFalso(fallas=[ErrorHTTPFalso(429, headers={"Retry-After": "5"})])
    crear(cliente, espera=esperas.append).embed_query("x")
    assert esperas == [5.0]


def test_la_espera_tiene_tope():
    esperas: list[float] = []
    cliente = ClienteFalso(fallas=[ErrorHTTPFalso(429, headers={"Retry-After": "3600"})])
    crear(cliente, espera=esperas.append).embed_query("x")
    assert esperas == [ESPERA_MAXIMA_SEGUNDOS]


def test_reintenta_ante_tiempo_agotado_y_falla_de_red():
    cliente = ClienteFalso(fallas=[TimeoutError("lento"), ConnectionError("sin red")])
    assert len(crear(cliente).embed_query("x")) == DIMENSION
    assert len(cliente.llamadas) == 3


def test_agota_los_reintentos_y_avisa():
    cliente = ClienteFalso(fallas=[ErrorHTTPFalso(503)] * 4)
    with pytest.raises(ErrorEmbeddings) as info:
        crear(cliente, reintentos=3).embed_query("x")
    assert info.value.codigo == e.EMBEDDINGS_NO_DISPONIBLE
    assert len(cliente.llamadas) == 4


def test_tiempo_agotado_sin_reintentos():
    with pytest.raises(ErrorEmbeddings) as info:
        crear(ClienteFalso(fallas=[TimeoutError()]), reintentos=0).embed_query("x")
    assert info.value.codigo == e.EMBEDDINGS_TIEMPO_AGOTADO


@pytest.mark.parametrize(
    "estado,codigo",
    [
        (401, e.EMBEDDINGS_TOKEN_INVALIDO),
        (403, e.EMBEDDINGS_TOKEN_INVALIDO),
        (402, e.EMBEDDINGS_SIN_CREDITOS),
        (404, e.EMBEDDINGS_MODELO_NO_ENCONTRADO),
        (400, e.EMBEDDINGS_ENTRADA_INVALIDA),
        (413, e.EMBEDDINGS_ENTRADA_INVALIDA),
        (422, e.EMBEDDINGS_ENTRADA_INVALIDA),
    ],
)
def test_errores_que_no_se_reintentan(estado, codigo):
    esperas: list[float] = []
    cliente = ClienteFalso(fallas=[ErrorHTTPFalso(estado)])
    with pytest.raises(ErrorEmbeddings) as info:
        crear(cliente, espera=esperas.append).embed_query("x")
    assert info.value.codigo == codigo
    assert len(cliente.llamadas) == 1
    assert esperas == []


def test_error_desconocido_se_traduce_sin_reintentar():
    cliente = ClienteFalso(fallas=[RuntimeError("algo raro")])
    with pytest.raises(ErrorEmbeddings) as info:
        crear(cliente).embed_query("x")
    assert info.value.codigo == e.EMBEDDINGS_ERROR
    assert len(cliente.llamadas) == 1


# =============================================================================
# 6. Token: nunca se expone
# =============================================================================


def test_sin_token_construye_pero_falla_con_un_error_claro_al_usarse():
    emb = EmbeddingsE5(ConfigRAG(hf_token=None))  # sin cliente: intentaría crear el real
    with pytest.raises(ErrorEmbeddings) as info:
        emb.embed_query("x")
    assert info.value.codigo == e.EMBEDDINGS_SIN_TOKEN
    assert "HF_TOKEN" in info.value.detalle
    assert "HF_TOKEN" not in info.value.mensaje


def test_el_token_nunca_aparece_en_el_error():
    otro_token = "hf_" + "Z" * 30
    falla = ErrorHTTPFalso(401, mensaje=f"token {TOKEN} rechazado; también {otro_token}")
    with pytest.raises(ErrorEmbeddings) as info:
        crear(ClienteFalso(fallas=[falla])).embed_query("x")
    texto = str(info.value)
    assert TOKEN not in texto and otro_token not in texto
    assert "***" in texto


def test_el_token_no_aparece_en_repr():
    assert TOKEN not in repr(crear(ClienteFalso()))


def test_mensaje_para_el_usuario_no_trae_detalles_tecnicos():
    with pytest.raises(ErrorEmbeddings) as info:
        crear(ClienteFalso(fallas=[ErrorHTTPFalso(402)])).embed_query("x")
    assert "HTTP" not in info.value.mensaje
    assert "HTTP 402" in info.value.detalle


# =============================================================================
# 7. Cómo se arma el cliente real (hallazgo de la prueba en vivo)
# =============================================================================


class ClienteRegistrador:
    """Reemplaza a InferenceClient para ver con qué argumentos se crea."""

    creaciones: list[dict] = []

    def __init__(self, **kwargs):
        ClienteRegistrador.creaciones.append(kwargs)


@pytest.fixture()
def registrador(monkeypatch):
    ClienteRegistrador.creaciones = []
    monkeypatch.setattr("huggingface_hub.InferenceClient", ClienteRegistrador)
    return ClienteRegistrador.creaciones


def test_con_hf_inference_usa_la_url_del_pipeline(registrador):
    EmbeddingsE5(ConfigRAG(hf_token=TOKEN, timeout_segundos=12))._obtener_cliente()
    (argumentos,) = registrador
    assert argumentos["model"] == (
        "https://router.huggingface.co/hf-inference/models/intfloat/multilingual-e5-base/pipeline/feature-extraction"
    )
    assert "provider" not in argumentos
    assert argumentos["token"] == TOKEN and argumentos["timeout"] == 12


def test_una_url_propia_manda(registrador):
    EmbeddingsE5(ConfigRAG(hf_token=TOKEN, url_embeddings="https://mi-endpoint.ejemplo/embed"))._obtener_cliente()
    assert registrador[0]["model"] == "https://mi-endpoint.ejemplo/embed"


def test_otro_proveedor_usa_la_ruta_de_huggingface_hub(registrador):
    EmbeddingsE5(ConfigRAG(hf_token=TOKEN, proveedor_embeddings="otro-proveedor"))._obtener_cliente()
    assert registrador[0]["model"] == "intfloat/multilingual-e5-base"
    assert registrador[0]["provider"] == "otro-proveedor"


def test_url_de_embeddings():
    assert url_de_embeddings(ConfigRAG()) == URL_HF_INFERENCE.format(modelo="intfloat/multilingual-e5-base")
    assert url_de_embeddings(ConfigRAG(proveedor_embeddings="otro")) is None


def test_el_cliente_se_crea_una_sola_vez(registrador):
    emb = EmbeddingsE5(ConfigRAG(hf_token=TOKEN))
    assert emb._obtener_cliente() is emb._obtener_cliente()
    assert len(registrador) == 1


# =============================================================================
# 8. Estadísticas, parámetros y compatibilidad con LangChain
# =============================================================================


def test_estadisticas_cuentan_peticiones_textos_y_caracteres():
    emb = crear(ClienteFalso(), tamano_lote=2)
    emb.embed_documents(["abc", "de", "f"])
    datos = emb.estadisticas.como_dict()
    assert datos["peticiones"] == 2
    assert datos["textos"] == 3
    # Los caracteres cuentan con el prefijo, que también se envía.
    assert datos["caracteres"] == len("passage: abc") + len("passage: de") + len("passage: f")


def test_pasa_los_parametros_de_la_api_al_cliente():
    cliente = ClienteFalso()
    crear(cliente, parametros_api={"truncate": True}).embed_query("x")
    assert cliente.kwargs == [{"truncate": True}]


def test_es_un_embeddings_de_langchain_y_funciona_en_async():
    emb = crear(ClienteFalso())
    assert isinstance(emb, Embeddings)
    vector = asyncio.run(emb.aembed_query("Scrum Master"))
    assert len(vector) == DIMENSION
