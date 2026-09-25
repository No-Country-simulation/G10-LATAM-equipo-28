"""
Cliente_agemte.py

Cliente MCP reusable: conexión a servidor_objeStorageOracle.py + carga de
tools para LangChain + interpretación de resultados. El Buscador de
Documentos y el resto de los agentes de NuevaMente importan estas
funciones en vez de reimplementar la conexión cada uno.

Mismo patrón que Cliente_agemte.py, 
al servidor de Object Storage de este proyecto.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

logger = logging.getLogger("nuevamente.cliente_mcp")

MAX_REINTENTOS_CONEXION = 2  # 1 intento inicial + 2 reintentos = 3 intentos totales


@asynccontextmanager
async def conectar_mcp():
    """
    Conecta con el servidor MCP de Object Storage (servidor_objeStorageOracle.py)
    vía stdio y entrega una ClientSession ya inicializada, lista para usar.
    """
    parametros_servidor = StdioServerParameters(
        command="python",
        args=["servidor_objeStorageOracle.py"],
    )

    async with stdio_client(parametros_servidor) as (lectura, escritura):
        async with ClientSession(lectura, escritura) as sesion:
            await sesion.initialize()
            yield sesion


async def obtener_tools_langchain(sesion: ClientSession):
    """
    Carga las tools expuestas por servidor_objeStorageOracle.py ya envueltas
    como BaseTool de LangChain (listar_documentos_fuente, subir_documento_fuente,
    descargar_documento, guardar_resultado, guardar_resultado_formateado),
    listas para bind_tools() o para llamar directo por nombre.
    """
    return await load_mcp_tools(sesion)


def extraer_texto_resultado(resultado_tool) -> str:
    """load_mcp_tools devuelve el contenido como lista de dicts
    [{'type': 'text', 'text': '...'}] -- extrae el texto plano."""
    if isinstance(resultado_tool, list) and resultado_tool:
        primero = resultado_tool[0]
        if isinstance(primero, dict) and "text" in primero:
            return primero["text"]
    return str(resultado_tool)


async def con_reintento_mcp(coro_factory, max_reintentos: int = MAX_REINTENTOS_CONEXION):
    """
    Reintenta una operación completa contra el servidor MCP (conexión +
    trabajo) ante fallos transitorios -- ej. el subproceso de
    servidor_objeStorageOracle.py tarda en levantar o hay un hiccup de stdio.

    coro_factory: función SIN argumentos que, al llamarla, devuelve la
    corutina completa a ejecutar (típicamente envuelve el
    `async with conectar_mcp() as sesion: ...` entero del nodo que la usa).
    """
    ultimo_error: Exception | None = None
    for intento in range(1, max_reintentos + 2):  # +2: 1 inicial + los reintentos
        try:
            return await coro_factory()
        except Exception as e:
            ultimo_error = e
            logger.warning(f"[con_reintento_mcp] intento {intento} falló: {e}")
    raise ultimo_error


async def _prueba_conexion():
    """
    Prueba manual de conexión y listado de tools. No se usa en
    producción -- sirve para verificar que el servidor responde.
    """
    print("Iniciando conexión con el Servidor MCP...")

    async with conectar_mcp() as sesion:
        print("✅ Conectado exitosamente.\n")

        tools = await obtener_tools_langchain(sesion)

        print("🛠️ Herramientas cargadas para LangChain:")
        for tool in tools:
            print(f" - Nombre: {tool.name}")
            print(f" - Descripción: {tool.description}\n")

        print("🤖 Ejecutando 'listar_documentos_fuente' para chequear el bucket...\n")
        tool_listar = next(t for t in tools if t.name == "listar_documentos_fuente")

        resultado = await tool_listar.ainvoke({})

        print("📄 Datos devueltos:")
        print(extraer_texto_resultado(resultado))


if __name__ == "__main__":
    asyncio.run(_prueba_conexion())