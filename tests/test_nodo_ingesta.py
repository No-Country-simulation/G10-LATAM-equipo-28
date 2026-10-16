"""Pruebas del nodo Ingesta del grafo: descarga por MCP + indexado en el RAG.

Verifican el contrato del nodo sin red ni modelo de embeddings (se reemplazan
`conectar_mcp`, las herramientas y `indexar_documento` por dobles).

Ejecutar:   pytest tests/test_nodo_ingesta.py -v
"""

from __future__ import annotations

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import grafo  # noqa: E402
from src.rag.errores import RAG_DOCUMENTO_VACIO, ErrorRAG  # noqa: E402

NOMBRE = "guia.md"
TEXTO = "Una VCN es una red privada y personalizable en la nube."


class Tool:
    def __init__(self, name: str) -> None:
        self.name = name

    async def ainvoke(self, _datos):
        valor = {"nombre": NOMBRE, "texto_extraido": TEXTO}
        return [{"type": "text", "text": json.dumps(valor)}]


@asynccontextmanager
async def _conectar():
    yield object()


async def _tools(_sesion):
    return [Tool("descargar_documento")]


def _preparar(monkeypatch, indexar) -> None:
    monkeypatch.setattr(grafo, "conectar_mcp", _conectar)
    monkeypatch.setattr(grafo, "obtener_tools_langchain", _tools)
    monkeypatch.setattr(grafo, "indexar_documento", indexar)


def test_ingesta_indexa_el_documento_y_fija_document_id(monkeypatch):
    llamadas: dict[str, str] = {}

    def indexar_falso(document_id: str, texto: str) -> int:
        llamadas["document_id"] = document_id
        llamadas["texto"] = texto
        return 3

    _preparar(monkeypatch, indexar_falso)

    salida = asyncio.run(grafo.nodo_ingesta({"objeto_id_confirmado": f"fuentes/{NOMBRE}"}))

    assert salida["documento_titulo"] == NOMBRE
    assert salida["documento_contenido"] == TEXTO
    assert salida["document_id"] == llamadas["document_id"]
    assert llamadas["texto"] == TEXTO
    assert salida["fuente_confirmada"] is None  # hay que reconfirmar cobertura


def test_ingesta_si_el_indexado_falla_devuelve_error_sin_titulo(monkeypatch):
    def indexar_que_falla(document_id: str, texto: str) -> int:
        raise ErrorRAG("El documento no tiene texto.", codigo=RAG_DOCUMENTO_VACIO)

    _preparar(monkeypatch, indexar_que_falla)

    salida = asyncio.run(grafo.nodo_ingesta({"objeto_id_confirmado": f"fuentes/{NOMBRE}"}))

    assert salida["status"] == "error"
    assert salida["error"]
    assert "documento_titulo" not in salida


def test_ingesta_con_objeto_invalido_no_descarga_ni_indexa(monkeypatch):
    def indexar_no_deberia_llamarse(document_id: str, texto: str) -> int:
        raise AssertionError("no debía indexar con un objeto_id inválido")

    _preparar(monkeypatch, indexar_no_deberia_llamarse)

    salida = asyncio.run(grafo.nodo_ingesta({"objeto_id_confirmado": ""}))

    assert salida["status"] == "error"
    assert salida["validacion_entrada_ok"] is False
