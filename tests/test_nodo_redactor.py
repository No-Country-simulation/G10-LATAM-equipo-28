from __future__ import annotations

import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from test_agente_redactor_pedagogico import SPEC, FakeGenerator, salida_valida, solicitud
from src.agentes.generador_llm_client import GeneradorLLMClient
from src.agentes.redactor import construir_nodo_redactor, enrutar_tras_redactor
from src.contracts import SolicitudAdaptacion
from src.errores import ErrorLLM


def state_base():
    return {
        "fuente_confirmada": True,
        "chunks_fuente_confirmados": [{
            "chunk_id": "chunk-1", "texto": "Una VCN es una red privada en la nube.",
            "score": 0.91, "pagina": 1, "document_id": "doc-original",
        }],
        "intentos_redactor": 0,
        "contenido_adaptado": {"titulo": "Generación anterior"},
        "metadatos": {"conceptos_clave": ["anterior"]},
        "evaluacion_calidad": {"observaciones": "Feedback anterior"},
        "aprobado": True,
        "error": "Fallo anterior",
    }


def ejecutar(state, generador=None, formato="Flashcards", preparar=None, obtener=None):
    gen = generador or FakeGenerator(salida_valida(formato))
    nodo = construir_nodo_redactor(gen, preparar or (lambda *_: SPEC),
                                   obtener or (lambda _: solicitud(formato)))
    return asyncio.run(nodo(state)), gen


@pytest.mark.parametrize("formato", ["Flashcards", "Tutorial", "Quiz", "Resumen Ejecutivo"])
def test_state_valido_produce_contenido_y_metadatos_de_los_cuatro_formatos(formato):
    state = state_base()
    original = deepcopy(state)
    parametros = []
    resultado, gen = ejecutar(state, formato=formato,
                              preparar=lambda *args: parametros.append(args) or SPEC)
    assert parametros == [(solicitud(formato).perfil_destinatario,
                           solicitud(formato).nivel_detalle)]
    assert resultado["contenido_adaptado"]["items"][0]["anclaje"] == ["chunk-1"]
    assert resultado["metadatos"]["formato_generado"] == formato
    assert resultado["metadatos"]["nivel_detalle_aplicado"] == "Didactico"
    assert resultado["metadatos"]["prerrequisitos"] == []
    assert resultado["intentos_redactor"] == 1
    assert resultado["aprobado"] is None and resultado["evaluacion_calidad"] is None
    assert resultado["error"] is None and "status" not in resultado
    assert "Feedback anterior" not in gen.prompt
    assert "doc-original" not in gen.prompt
    assert state == original
    assert enrutar_tras_redactor({**state, **resultado}) == "critico_revisor"


@pytest.mark.parametrize("chunks", [
    [{"id": "chunk-1", "texto": "Fuente con ID", "score": 0.9}],
    [SimpleNamespace()],
])
def test_no_inventa_identidad_para_objetos_sin_dto(chunks):
    resultado, gen = ejecutar({**state_base(), "chunks_fuente_confirmados": chunks})
    if isinstance(chunks[0], dict):
        assert resultado["error"] is None
    else:
        assert resultado["error"] and not gen.prompt


def test_acepta_modelo_rag_y_conserva_identidad_del_anclaje():
    class ChunkRag(BaseModel):
        chunk_id: str
        texto: str
        document_id: str
        score: float
    chunk = ChunkRag(chunk_id="chunk-1", texto="Una VCN es una red privada.",
                     document_id="doc-original", score=0.91)
    resultado, _ = ejecutar({**state_base(), "chunks_fuente_confirmados": [chunk]})
    assert resultado["contenido_adaptado"]["items"][0]["anclaje"] == [chunk.chunk_id]
    assert chunk.document_id == "doc-original"


@pytest.mark.parametrize("chunks", [
    ["Texto sin identidad"],
    [{"texto": "Texto sin identidad"}],
    [{"id": "uno", "chunk_id": "otro", "texto": "Texto"}],
    [{"id": "chunk-1", "texto": "A"}, {"id": "chunk-1", "texto": "B"}],
    "texto suelto",
])
def test_chunks_invalidos_no_llaman_llm_ni_dejan_generacion_anterior(chunks):
    resultado, gen = ejecutar({**state_base(), "chunks_fuente_confirmados": chunks})
    assert resultado["status"] == "error" and resultado["error"]
    assert resultado["contenido_adaptado"] is None and resultado["metadatos"] is None
    assert resultado["aprobado"] is False and resultado["evaluacion_calidad"] is None
    assert resultado["intentos_redactor"] == 0 and not gen.prompt
    assert enrutar_tras_redactor(resultado) == "error"


@pytest.mark.parametrize("fuente,chunks", [(False, None), (None, None), (True, []), (True, None)])
def test_abstencion_sin_fuente_no_genera(fuente, chunks):
    resultado, gen = ejecutar({**state_base(), "fuente_confirmada": fuente,
                              "chunks_fuente_confirmados": chunks})
    assert resultado["contenido_adaptado"] is None and resultado["status"] == "error"
    assert not gen.prompt and resultado["intentos_redactor"] == 0


@pytest.mark.parametrize("salida", [
    ErrorLLM("Detalle privado", mensaje_usuario="Detalle privado"),
    {"estado": "EVIDENCIA_INSUFICIENTE", "motivo_abstencion": "Detalle privado"},
    {"estado": "GENERACION_CON_EVIDENCIA", "contenido": {"items": []}},
])
def test_error_y_abstencion_del_generador_detienen_ruta_y_ocultan_detalles(salida):
    resultado, gen = ejecutar(state_base(), FakeGenerator(salida))
    assert gen.prompt and resultado["intentos_redactor"] == 1
    assert resultado["contenido_adaptado"] is None
    assert resultado["status"] == "error" and "Detalle privado" not in resultado["error"]
    assert enrutar_tras_redactor(resultado) == "error"


def test_anchor_ajeno_se_rechaza_antes_de_propagarse_al_revisor():
    salida = salida_valida("Flashcards")
    salida["contenido"]["items"][0]["anclaje"] = ["chunk-ajeno"]
    resultado, _ = ejecutar(state_base(), FakeGenerator(salida))
    assert resultado["contenido_adaptado"] is None and resultado["intentos_redactor"] == 1


def test_feedback_existente_se_envia_en_reintento_sin_reintentar_dentro_del_nodo():
    resultado, gen = ejecutar({**state_base(), "intentos_redactor": 1})
    assert "Feedback anterior" in gen.prompt
    assert resultado["intentos_redactor"] == 2 and resultado["aprobado"] is None


@pytest.mark.parametrize("obtener", [
    lambda _: {},
    lambda _: SolicitudAdaptacion.model_construct(documento_titulo="Sin contenido"),
])
def test_solicitud_incompleta_no_llama_generador(obtener):
    resultado, gen = ejecutar(state_base(), obtener=obtener)
    assert resultado["status"] == "error" and not gen.prompt
    assert resultado["intentos_redactor"] == 0


def test_spec_incompleta_no_llama_generador():
    resultado, gen = ejecutar(state_base(), preparar=lambda *_: {"bloom": "Entender"})
    assert resultado["status"] == "error" and not gen.prompt
    assert resultado["intentos_redactor"] == 0


def test_llamada_al_adapter_respeta_get_llm_y_rate_limiter_inyectados():
    llamadas = []
    limiter = object()
    class Cliente:
        def with_structured_output(self, output_model):
            self.output_model = output_model
            return self
        def invoke(self, mensajes):
            assert self.output_model.__name__ == "RespuestaGenerador"
            assert mensajes and "chunk-1" in str(mensajes)
            return self.output_model.model_validate(salida_valida("Flashcards"))
    def get_llm(**kwargs):
        llamadas.append(kwargs)
        return Cliente()
    resultado, _ = ejecutar(state_base(), GeneradorLLMClient(get_llm, limiter))
    assert len(llamadas) == 1 and llamadas[0]["rate_limiter"] is limiter
    assert llamadas[0]["max_tokens"] == 4096
    assert resultado["intentos_redactor"] == 1 and resultado["error"] is None


@pytest.mark.parametrize("salida,ruta", [
    (salida_valida("Flashcards"), "critico_revisor"),
    (ErrorLLM("Fallo técnico"), "error"),
])
def test_composicion_langgraph_con_canales_actuales_y_ruta_condicional(salida, ruta):
    from langgraph.graph import END, START, StateGraph
    from src.agent_state import AgentState

    visitados = []
    def siguiente(state):
        visitados.append(state["contenido_adaptado"]["items"][0]["anclaje"])
        return {}
    builder = StateGraph(AgentState)
    builder.add_node("redactor_pedagogico", construir_nodo_redactor(
        FakeGenerator(salida), lambda *_: SPEC, lambda _: solicitud("Flashcards")))
    builder.add_node("critico_revisor", siguiente)
    builder.add_edge(START, "redactor_pedagogico")
    builder.add_conditional_edges("redactor_pedagogico", enrutar_tras_redactor,
                                 {"critico_revisor": "critico_revisor", "error": END})
    builder.add_edge("critico_revisor", END)
    resultado = asyncio.run(builder.compile().ainvoke(state_base()))
    assert resultado["intentos_redactor"] == 1
    assert enrutar_tras_redactor(resultado) == ruta
    assert visitados == ([["chunk-1"]] if ruta == "critico_revisor" else [])
