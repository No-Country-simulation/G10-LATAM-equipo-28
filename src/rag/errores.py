"""
NuevaMente — Errores del RAG.

Cada error lleva tres datos:

  - `codigo`:  identificador estable. Lo usan el grafo y las pruebas.
  - `mensaje`: texto apto para el usuario final, sin trazas, rutas, nombres
               internos ni claves. Es lo único que debe mostrar la interfaz.
  - `detalle`: pista técnica para los registros y para quien desarrolla
               (variables del .env, código HTTP). Nunca incluye claves.

`str(error)` junta los tres, pensado para la consola y los registros.
"""

from __future__ import annotations

# =============================================================================
# Códigos
# =============================================================================

RAG_CONFIGURACION = "RAG_CONFIGURACION"
RAG_FORMATO_NO_SOPORTADO = "RAG_FORMATO_NO_SOPORTADO"
RAG_DOCUMENTO_VACIO = "RAG_DOCUMENTO_VACIO"
RAG_DOCUMENTO_NO_INDEXADO = "RAG_DOCUMENTO_NO_INDEXADO"
RAG_CHUNK_NO_ENCONTRADO = "RAG_CHUNK_NO_ENCONTRADO"
RAG_CONSULTA_VACIA = "RAG_CONSULTA_VACIA"
RAG_INDICE = "RAG_INDICE"

EMBEDDINGS_ERROR = "EMBEDDINGS_ERROR"
EMBEDDINGS_SIN_TOKEN = "EMBEDDINGS_SIN_TOKEN"
EMBEDDINGS_TOKEN_INVALIDO = "EMBEDDINGS_TOKEN_INVALIDO"
EMBEDDINGS_SIN_CREDITOS = "EMBEDDINGS_SIN_CREDITOS"
EMBEDDINGS_MODELO_NO_ENCONTRADO = "EMBEDDINGS_MODELO_NO_ENCONTRADO"
EMBEDDINGS_ENTRADA_INVALIDA = "EMBEDDINGS_ENTRADA_INVALIDA"
EMBEDDINGS_LIMITE = "EMBEDDINGS_LIMITE"
EMBEDDINGS_NO_DISPONIBLE = "EMBEDDINGS_NO_DISPONIBLE"
EMBEDDINGS_TIEMPO_AGOTADO = "EMBEDDINGS_TIEMPO_AGOTADO"
EMBEDDINGS_RESPUESTA_INVALIDA = "EMBEDDINGS_RESPUESTA_INVALIDA"


# =============================================================================
# Excepciones
# =============================================================================


class ErrorRAG(Exception):
    """Base de todos los errores del RAG."""

    codigo_por_defecto = "RAG_ERROR"

    def __init__(self, mensaje: str, *, codigo: str | None = None, detalle: str = "") -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo or self.codigo_por_defecto
        self.detalle = detalle

    def __str__(self) -> str:
        texto = f"[{self.codigo}] {self.mensaje}"
        return f"{texto} Detalle: {self.detalle}" if self.detalle else texto


class ErrorConfiguracionRAG(ErrorRAG):
    """Un valor del .env falta o no es válido."""

    codigo_por_defecto = RAG_CONFIGURACION


class ErrorEmbeddings(ErrorRAG):
    """No se pudieron calcular los embeddings (API o respuesta inesperada)."""

    codigo_por_defecto = EMBEDDINGS_ERROR
