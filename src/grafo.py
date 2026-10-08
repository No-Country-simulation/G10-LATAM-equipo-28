"""
grafo.py

Grafo de NuevaMente (5to spec). Flujo secuencial, no fan-out:

buscador_documentos -> confirmar_ejecucion (HITL) -> ingesta -> validacion
-> supervisor -> investigador -> redactor_pedagogico -> critico_revisor
-> guardado_final -> confirmar_modificacion (HITL) -> [modificador -> critico_revisor
   -> guardado_final -> confirmar_modificacion]* -> END

Nodos REALES (llaman a OCI vía Cliente_agemte.py, ya validado):
  - buscador_documentos, ingesta (descarga), guardado_final

Nodos con LLM real:
  - supervisor (agentes/supervisor.py, IntencionOut vía Groq)
  - redactor_pedagogico (core real con dependencias inyectadas)
  - critico_revisor (agentes/critico_revisor.py, formato + fidelidad cualitativa)
  - modificador (agentes/modificador.py, cambio puntual sobre lo aprobado)
  - investigador (agentes/investigador.py) -- real solo si se inyecta un
    recuperador; por defecto sigue el stub porque rag/ (Chroma) no está en dev

Nodos STUB (marcados # TODO, esperando sus archivos):
  - validacion (seguridad/validadores.py pendiente)

HITL de aclaración (1 ronda): la rama "aclaracion" de enrutar_tras_investigador
entra a nodo_aclaracion, que pausa el grafo y expone el mensaje_aclaracion real
del agente_investigador.py; la respuesta se guarda en respuesta_aclaracion_usuario
y el grafo termina. app.py decide si reinicia con otro tema o pide otro documento.

Checkpointer: SqliteSaver con conexión manual (aiosqlite.connect()).

IMPORTANTE (evidencia de pruebas repetidas en Windows): con_reintento_mcp
en Cliente_agemte.py NO usa timeout (ni asyncio.wait_for ni
anyio.fail_after) -- envolver la llamada en cualquier cancel scope
provoca cuelgues consistentes del subproceso MCP en el ProactorEventLoop
de Windows. El cuelgue intermitente que queda (sin wrapper) se resuelve
reintentando la corrida manualmente; no bloquea el desarrollo, y es
poco probable que aparezca igual en producción (Linux).
"""

from __future__ import annotations

import json
import re

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from src.agent_state import AgentState
from src.agentes.generador_llm_client import GeneradorLLMClient
from src.agentes.critico_revisor import construir_nodo_critico_revisor
from src.agentes.modificador import construir_nodo_modificador
from src.agentes.redactor import (
    construir_nodo_redactor, enrutar_tras_redactor, obtener_solicitud_redactor,
)
from src.Cliente_agemte import conectar_mcp, con_reintento_mcp, extraer_texto_resultado, extraer_lista_resultado, obtener_tools_langchain
from src.seguridad.rate_limiter import RateLimiter
from src.seguridad.permisos import obtener_herramienta_autorizada
from src.seguridad.validadores import (
    ErrorValidacionEntrada,
    mensajes_con_entrada_sanitizada,
    validar_entrada_pre_llm,
    validar_instruccion_modificacion,
    validar_objeto_fuente,
    validar_solicitud_adaptacion,
    validar_tema_consulta,
)

PREFIJO_FUENTES = "fuentes/"
MAX_REINTENTOS_REDACTOR = 2
MAX_VUELTAS_MODIFICACION = 5


# --------------------------------------------------------------------------
# Buscador de Documentos (REAL, determinístico -- 5to spec)
# --------------------------------------------------------------------------

def _matchear_documentos(tema: str, documentos: list[dict]) -> list[str]:
    """
    Match determinístico por nombre de archivo, sin LLM (mismo principio
    de "acceso a OCI no agéntico" ya confirmado para Ingesta/Guardado).
    Devuelve la lista de nombres (sin prefijo) que matchean.
    """
    tema_norm = tema.lower().strip()
    palabras_tema = {p for p in re.split(r"\W+", tema_norm) if len(p) > 2}

    candidatos = []
    for doc in documentos:
        nombre_norm = doc["nombre"].lower()
        if tema_norm in nombre_norm or any(p in nombre_norm for p in palabras_tema):
            candidatos.append(doc["nombre"])
    return candidatos


async def nodo_buscador_documentos(state: AgentState) -> dict:
    tema = state.get("tema_pedido_chat", "")

    async def _listar():
        async with conectar_mcp() as sesion:
            tools = await obtener_tools_langchain(sesion)
            herramienta = obtener_herramienta_autorizada(
                tools, etapa="buscador_documentos", nombre="listar_documentos_fuente"
            )
            resultado = await herramienta.ainvoke({})
            return extraer_lista_resultado(resultado)

    documentos = await con_reintento_mcp(_listar)
    candidatos = _matchear_documentos(tema, documentos)

    if len(candidatos) == 1:
        return {
            "objeto_id_confirmado": f"{PREFIJO_FUENTES}{candidatos[0]}",
            "candidatos_documento": [],
        }

    return {
        "objeto_id_confirmado": None,
        "candidatos_documento": candidatos if candidatos else [d["nombre"] for d in documentos],
    }


# --------------------------------------------------------------------------
# HITL: ¿Ejecutar? (REAL -- 5to spec)
# --------------------------------------------------------------------------

def nodo_confirmar_ejecucion(state: AgentState) -> dict:
    """
    Pausa el grafo hasta que la UI resuma con Command(resume=...).
    Se espera un dict como el de vuelta: {"confirmado": bool, "objeto_id_confirmado": str | None}
    -- si la UI dejó elegir un candidato del selectbox, viene acá.
    """
    respuesta = interrupt({
        "tipo": "confirmar_ejecucion",
        "candidatos_documento": state.get("candidatos_documento", []),
        "objeto_id_confirmado": state.get("objeto_id_confirmado"),
    })

    objeto_id = respuesta.get("objeto_id_confirmado") or state.get("objeto_id_confirmado")
    if objeto_id and not objeto_id.startswith(PREFIJO_FUENTES):
        objeto_id = f"{PREFIJO_FUENTES}{objeto_id}"

    return {
        "ejecucion_confirmada": bool(respuesta.get("confirmado", False)),
        "objeto_id_confirmado": objeto_id,
    }


def enrutar_tras_confirmar_ejecucion(state: AgentState) -> str:
    return "ingesta" if state.get("ejecucion_confirmada") else "cancelado"


# --------------------------------------------------------------------------
# Ingesta (descarga REAL vía Cliente_agemte; chunking/Chroma -- TODO, rag/ pendiente)
# --------------------------------------------------------------------------

async def nodo_ingesta(state: AgentState) -> dict:
    try:
        objeto_id = validar_objeto_fuente(state.get("objeto_id_confirmado"))
    except ErrorValidacionEntrada as exc:
        return {
            "validacion_entrada_ok": False,
            "status": "error",
            "error": exc.mensaje,
        }

    async def _descargar():
        async with conectar_mcp() as sesion:
            tools = await obtener_tools_langchain(sesion)
            herramienta = obtener_herramienta_autorizada(
                tools, etapa="ingesta", nombre="descargar_documento"
            )
            resultado = await herramienta.ainvoke({"objeto_id": objeto_id})
            texto = extraer_texto_resultado(resultado)
            return json.loads(texto)

    documento = await con_reintento_mcp(_descargar)

    # TODO (rag/ pendiente): chunking + embeddings (HuggingFace multilingual-e5-base)
    # + indexado en Chroma (colección documento_activo, umbral 0.78).
    # Conserva la fuente real para SolicitudAdaptacion. Invalida evidencia de
    # una ejecución anterior; RAG/Investigador deben confirmar la nueva fuente.
    return {
        "estado": "ingesta_completada",
        "documento_titulo": documento["nombre"],
        "documento_contenido": documento["texto_extraido"],
        "chunks_fuente_estructurados": None,
        "fuente_confirmada": None,
    }


# --------------------------------------------------------------------------
# Validación de entrada antes de llamar a cualquier agente LLM.
# --------------------------------------------------------------------------

def _estado_error_validacion(mensaje: str) -> dict:
    """Corta una ejecución inválida y descarta cualquier salida anterior reutilizable."""
    return {
        "validacion_entrada_ok": False,
        "status": "error",
        "error": mensaje,
        "contenido_adaptado": None,
        "metadatos": None,
        "evaluacion_calidad": None,
        "aprobado": False,
        "almacenamiento_oci": None,
    }

def nodo_validacion(state: AgentState) -> dict:
    try:
        entrada = validar_entrada_pre_llm(state)
    except ErrorValidacionEntrada as exc:
        return _estado_error_validacion(exc.mensaje)
    return {
        "tema_pedido_chat": entrada.tema_pedido_chat,
        "input_sanitizado": entrada.mensaje_usuario,
        "validacion_entrada_ok": True,
        "error": None,
    }


def enrutar_tras_validacion(state: AgentState) -> str:
    return "ok" if state.get("validacion_entrada_ok") is True else "rechazado"


def nodo_validacion_solicitud(state: AgentState) -> dict:
    """Comprueba la salida del Supervisor contra el contrato antes del Investigador."""
    try:
        validar_solicitud_adaptacion(state)
        tema = validar_tema_consulta(state.get("tema_consulta"))
    except ErrorValidacionEntrada as exc:
        return _estado_error_validacion(exc.mensaje)
    return {"tema_consulta": tema, "validacion_entrada_ok": True, "error": None}


def enrutar_tras_validacion_solicitud(state: AgentState) -> str:
    return "ok" if state.get("validacion_entrada_ok") is True else "rechazado"


def nodo_validacion_modificacion(state: AgentState) -> dict:
    """Valida el cambio pedido antes de delegarlo al Modificador."""
    instruccion = state.get("instruccion_modificacion")
    if not instruccion:
        return {"validacion_entrada_ok": True, "error": None}
    try:
        normalizada = validar_instruccion_modificacion(instruccion)
    except ErrorValidacionEntrada as exc:
        return {
            "validacion_entrada_ok": False,
            "status": "error",
            "error": exc.mensaje,
        }
    return {
        "instruccion_modificacion": normalizada,
        "validacion_entrada_ok": True,
        "error": None,
    }


def enrutar_tras_validacion_modificacion(state: AgentState) -> str:
    if state.get("validacion_entrada_ok") is not True:
        return "rechazado"
    return "modificar" if state.get("instruccion_modificacion") else "fin"


# --------------------------------------------------------------------------
# Investigador RAG (STUB)
# --------------------------------------------------------------------------

def nodo_investigador(state: AgentState) -> dict:
    # TODO: consulta real a Chroma (rag/vectorstore.py pendiente).
    # Stub siempre "confirma" para que el skeleton fluya de punta a punta.
    return {
        "fuente_confirmada": True,
        "chunks_fuente_confirmados": ["[STUB] chunk de ejemplo del documento"],
    }


def enrutar_tras_investigador(state: AgentState) -> str:
    return "match" if state.get("fuente_confirmada") else "aclaracion"


# --------------------------------------------------------------------------
# HITL: aclaración (1 ronda) -- REAL
# --------------------------------------------------------------------------

def nodo_aclaracion(state: AgentState) -> dict:
    """
    Pausa el grafo y expone el `mensaje_aclaracion` del Investigador.

    HITL de 1 ronda: la UI resume con Command(resume={"respuesta": str | None}).
    La respuesta se guarda en `respuesta_aclaracion_usuario` y el grafo termina;
    `app.py` decide si reinicia con otro tema o pide subir otro documento.
    """
    respuesta = interrupt({
        "tipo": "aclaracion",
        "mensaje_aclaracion": state.get("mensaje_aclaracion"),
    })
    return {"respuesta_aclaracion_usuario": respuesta.get("respuesta")}


# --------------------------------------------------------------------------
# Crítico/Revisor: enrutamiento tras la revisión
# --------------------------------------------------------------------------

def enrutar_tras_revisor(state: AgentState) -> str:
    if state.get("aprobado"):
        return "guardado_final"
    if state.get("intentos_redactor", 0) >= MAX_REINTENTOS_REDACTOR:
        return "guardado_final"  # agota reintentos -> exito_con_advertencias
    if state.get("vueltas_modificacion", 0) >= MAX_VUELTAS_MODIFICACION:
        return "guardado_final"  # tope de modificaciones -> evita loop indefinido
    if state.get("vueltas_modificacion", 0) > 0:
        return "modificador"
    return "redactor_pedagogico"


# --------------------------------------------------------------------------
# Guardado final (REAL -- usa guardar_resultado_formateado, ya validado)
# --------------------------------------------------------------------------

async def nodo_guardado_final(state: AgentState) -> dict:
    nombre_archivo = state["objeto_id_confirmado"].replace(PREFIJO_FUENTES, "", 1)
    contenido = {
        "status": "exito" if state.get("intentos_redactor", 0) < MAX_REINTENTOS_REDACTOR else "exito_con_advertencias",
        "metadatos": state.get("metadatos", {}),
        "contenido_adaptado": state.get("contenido_adaptado", {}),
        "evaluacion_calidad": state.get("evaluacion_calidad", {}),
    }

    async def _guardar():
        async with conectar_mcp() as sesion:
            tools = await obtener_tools_langchain(sesion)
            herramienta = obtener_herramienta_autorizada(
                tools, etapa="guardado_final", nombre="guardar_resultado_formateado"
            )
            resultado = await herramienta.ainvoke({
                "nombre_archivo": nombre_archivo,
                "contenido": contenido,
            })
            texto = extraer_texto_resultado(resultado)
            return json.loads(texto)

    almacenamiento_oci = await con_reintento_mcp(_guardar)

    return {
        "almacenamiento_oci": almacenamiento_oci,
        "status": contenido["status"],
    }


# --------------------------------------------------------------------------
# HITL: ¿Modificar? (REAL)
# --------------------------------------------------------------------------

def enrutar_tras_guardado(state: AgentState) -> str:
    if state.get("vueltas_modificacion", 0) >= MAX_VUELTAS_MODIFICACION:
        return "tope_alcanzado"
    return "preguntar"


def nodo_confirmar_modificacion(state: AgentState) -> dict:
    respuesta = interrupt({
        "tipo": "confirmar_modificacion",
        "vueltas_modificacion": state.get("vueltas_modificacion", 0),
    })
    return {
        "instruccion_modificacion": respuesta.get("instruccion"),
    }


# --------------------------------------------------------------------------
# Construcción del grafo
# --------------------------------------------------------------------------

async def construir_grafo(
    rate_limiter: RateLimiter | None = None,
    *,
    preparar_pedagogia=None,
    get_llm_factory=None,
    construir_supervisor=None,
    construir_critico_revisor=None,
    construir_modificador=None,
    recuperador=None,
):
    """
    rate_limiter: compartido entre los nodos con LLM real (hoy Supervisor
    y Redactor; se suma Investigador/Revisor/Modificador a medida que se
    escriben). Si no se pasa, se crea uno nuevo por default -- útil para
    scripts de prueba sueltos, pero en app.py conviene crear UNA instancia
    y reusarla entre reruns.

    preparar_pedagogia: preparar_explicacion_pedagogica de #3; puede
    inyectarse desde su composición, sin copiar el mapping.
    get_llm_factory: get_llm oficial; permite probar sin llamadas externas.
    construir_supervisor: factory(rate_limiter) -> nodo; conserva el patrón
    de dependencias inyectadas del carril de orquestación (Decisión A3: el
    grafo NO elige proveedor; se construye una vez en `app.py` y se inyecta).
    construir_critico_revisor: factory(rate_limiter) -> nodo del Revisor. El
    default usa el núcleo real; los tests inyectan un doble para fijar la
    aprobación/rechazo sin gastar cuota.
    construir_modificador: factory(rate_limiter) -> nodo del Modificador (mismo
    patrón). El default usa el núcleo real con la pedagogía y el validador de
    solicitud del Redactor.
    recuperador: vector store (rag/vectorstore.py). Si se pasa, el nodo
    Investigador real reemplaza al stub; si no, se mantiene el stub porque
    rag/ (Chroma) todavía no está en dev.
    """
    if rate_limiter is None:
        rate_limiter = RateLimiter()
    if preparar_pedagogia is None:
        from src.pedagogia.nodo import preparar_explicacion_pedagogica
        preparar_pedagogia = preparar_explicacion_pedagogica
    if get_llm_factory is None:
        from src.seguridad.llm_client import get_llm
        get_llm_factory = get_llm
    if construir_supervisor is None:
        from src.agentes.supervisor import construir_nodo_supervisor

        def construir_supervisor(rate_limiter):
            return construir_nodo_supervisor(
                GeneradorLLMClient(get_llm_factory, rate_limiter)
            )
    if construir_critico_revisor is None:
        def construir_critico_revisor(rate_limiter):
            return construir_nodo_critico_revisor(
                GeneradorLLMClient(get_llm_factory, rate_limiter)
            )
    if construir_modificador is None:
        def construir_modificador(rate_limiter):
            return construir_nodo_modificador(
                GeneradorLLMClient(get_llm_factory, rate_limiter),
                preparar_pedagogia,
                obtener_solicitud_redactor,
            )

    redactor = construir_nodo_redactor(
        GeneradorLLMClient(get_llm_factory, rate_limiter),
        preparar_pedagogia,
        obtener_solicitud_redactor,
    )

    if recuperador is None:
        nodo_investigador_activo = nodo_investigador
    else:
        from src.agentes.investigador import construir_nodo_investigador
        nodo_investigador_activo = construir_nodo_investigador(
            recuperador, GeneradorLLMClient(get_llm_factory, rate_limiter)
        )

    builder = StateGraph(AgentState)

    builder.add_node("buscador_documentos", nodo_buscador_documentos)
    builder.add_node("confirmar_ejecucion", nodo_confirmar_ejecucion)
    builder.add_node("ingesta", nodo_ingesta)
    builder.add_node("validacion", nodo_validacion)
    supervisor = construir_supervisor(rate_limiter)

    async def supervisor_con_entrada_sanitizada(state: AgentState) -> dict:
        estado_seguro = dict(state)
        estado_seguro["mensajes"] = mensajes_con_entrada_sanitizada(
            state.get("mensajes", []), state.get("input_sanitizado")
        )
        return await supervisor(estado_seguro)

    builder.add_node("supervisor", supervisor_con_entrada_sanitizada)
    builder.add_node("validacion_solicitud", nodo_validacion_solicitud)
    builder.add_node("investigador", nodo_investigador_activo)
    builder.add_node("aclaracion", nodo_aclaracion)
    builder.add_node("redactor_pedagogico", redactor)
    builder.add_node("critico_revisor", construir_critico_revisor(rate_limiter))
    builder.add_node("guardado_final", nodo_guardado_final)
    builder.add_node("confirmar_modificacion", nodo_confirmar_modificacion)
    builder.add_node("validacion_modificacion", nodo_validacion_modificacion)
    builder.add_node("modificador", construir_modificador(rate_limiter))

    builder.set_entry_point("buscador_documentos")

    builder.add_edge("buscador_documentos", "confirmar_ejecucion")
    builder.add_conditional_edges(
        "confirmar_ejecucion", enrutar_tras_confirmar_ejecucion,
        {"ingesta": "ingesta", "cancelado": END},
    )
    builder.add_edge("ingesta", "validacion")
    builder.add_conditional_edges(
        "validacion", enrutar_tras_validacion, {"rechazado": END, "ok": "supervisor"},
    )
    builder.add_edge("supervisor", "validacion_solicitud")
    builder.add_conditional_edges(
        "validacion_solicitud", enrutar_tras_validacion_solicitud,
        {"rechazado": END, "ok": "investigador"},
    )
    builder.add_conditional_edges(
        "investigador", enrutar_tras_investigador,
        {"match": "redactor_pedagogico", "aclaracion": "aclaracion"},
    )
    builder.add_edge("aclaracion", END)
    builder.add_conditional_edges(
        "redactor_pedagogico", enrutar_tras_redactor,
        {"critico_revisor": "critico_revisor", "error": END},
    )
    builder.add_conditional_edges(
        "critico_revisor", enrutar_tras_revisor,
        {
            "guardado_final": "guardado_final",
            "redactor_pedagogico": "redactor_pedagogico",
            "modificador": "modificador",
        },
    )
    builder.add_edge("modificador", "critico_revisor")
    builder.add_conditional_edges(
        "guardado_final", enrutar_tras_guardado,
        {"preguntar": "confirmar_modificacion", "tope_alcanzado": END},
    )
    builder.add_edge("confirmar_modificacion", "validacion_modificacion")
    builder.add_conditional_edges(
        "validacion_modificacion", enrutar_tras_validacion_modificacion,
        {"modificar": "modificador", "fin": END, "rechazado": END},
    )

    conexion = await aiosqlite.connect("checkpoints.sqlite")
    checkpointer = AsyncSqliteSaver(conexion)

    return builder.compile(checkpointer=checkpointer)
