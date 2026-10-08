"""Validación determinística de la entrada antes de delegarla a los agentes."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping

from pydantic import ValidationError

from src.config import settings
from src.contracts import SolicitudAdaptacion
from src.contracts.request import LONGITUD_MINIMA_CONTENIDO

MAX_LONGITUD_TEMA = 1_000
MAX_LONGITUD_MENSAJE = 12_000
MAX_LONGITUD_MODIFICACION = 2_000

_CONTROLES_NO_PERMITIDOS = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f-\x9f]")
_INYECCIONES_DIRECTAS = (
    re.compile(
        r"^\s*(?:ahora\s+)?(?:ignora|olvida|desatiende)\s+(?:todas?\s+)?"
        r"(?:las?\s+)?(?:instrucciones|reglas|pol[ií]ticas)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:ignore|forget|disregard)\s+(?:all\s+)?(?:the\s+)?"
        r"(?:previous|prior|above|system)\s+(?:instructions|rules|policies)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:revela|muestra|imprime|copia|env[ií]a)\s+(?:el\s+|la\s+)?"
        r"(?:prompt\s+del\s+sistema|system\s+prompt|clave|credencial|secreto|token)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:reveal|show|print|copy|send)\s+(?:the\s+)?"
        r"(?:system\s+prompt|api\s+key|credential|secret|token)\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class ErrorValidacionEntrada(ValueError):
    """Error seguro y estable para cortar el flujo antes de llamar a un LLM."""

    codigo: str
    mensaje: str

    def __str__(self) -> str:
        return self.mensaje


@dataclass(frozen=True)
class EntradaValidada:
    """Texto de usuario normalizado que se puede pasar al Supervisor."""

    mensaje_usuario: str | None
    tema_pedido_chat: str


def _texto_mensaje(mensaje: Any) -> tuple[str | None, bool]:
    if isinstance(mensaje, Mapping):
        tipo = str(mensaje.get("role") or mensaje.get("type") or "").lower()
        contenido = mensaje.get("content")
    else:
        tipo = str(getattr(mensaje, "type", "") or getattr(mensaje, "role", "")).lower()
        contenido = getattr(mensaje, "content", None)
    if tipo not in {"human", "user"}:
        return None, False
    return (contenido if isinstance(contenido, str) else None), True


def ultimo_mensaje_usuario(mensajes: Any) -> tuple[int | None, str | None]:
    """Obtiene el último mensaje humano sin asumir una clase de LangChain."""
    if not isinstance(mensajes, (list, tuple)):
        return None, None
    for indice in range(len(mensajes) - 1, -1, -1):
        texto, es_usuario = _texto_mensaje(mensajes[indice])
        if es_usuario:
            return indice, texto
    return None, None


def mensajes_con_entrada_sanitizada(mensajes: Any, texto: str | None) -> Any:
    """Copia el historial y reemplaza solo el texto humano ya normalizado."""
    if texto is None or not isinstance(mensajes, (list, tuple)):
        return mensajes
    copia = list(mensajes)
    indice, _ = ultimo_mensaje_usuario(copia)
    if indice is None:
        return mensajes
    original = copia[indice]
    if isinstance(original, Mapping):
        copia[indice] = {**original, "content": texto}
    elif hasattr(original, "model_copy"):
        copia[indice] = original.model_copy(update={"content": texto})
    else:
        raise ErrorValidacionEntrada(
            "MENSAJE_INVALIDO", "No se pudo preparar el mensaje de usuario de forma segura."
        )
    return copia


def normalizar_entrada_usuario(texto: str, *, campo: str, maximo: int) -> str:
    """Normaliza Unicode y saltos de línea sin borrar contenido silenciosamente."""
    normalizado = unicodedata.normalize("NFC", texto).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalizado:
        raise ErrorValidacionEntrada("ENTRADA_VACIA", f"El campo {campo} no puede quedar vacío.")
    if len(normalizado) > maximo:
        raise ErrorValidacionEntrada("ENTRADA_DEMASIADO_LARGA", f"El campo {campo} supera el límite permitido.")
    if _CONTROLES_NO_PERMITIDOS.search(normalizado):
        raise ErrorValidacionEntrada("CARACTERES_NO_PERMITIDOS", f"El campo {campo} contiene caracteres no permitidos.")
    return normalizado


def _detectar_instruccion_directa(texto: str) -> bool:
    """Busca órdenes directas de anulación o revelación, no vocabulario educativo."""
    inicio = texto[:1_000]
    return any(patron.search(inicio) for patron in _INYECCIONES_DIRECTAS)


def _validar_contenido_documento(contenido: Any) -> None:
    if not isinstance(contenido, str):
        raise ErrorValidacionEntrada("DOCUMENTO_INVALIDO", "El contenido del documento no tiene un formato válido.")
    if len(contenido.strip()) < LONGITUD_MINIMA_CONTENIDO:
        raise ErrorValidacionEntrada("DOCUMENTO_DEMASIADO_CORTO", "El documento no contiene texto suficiente para adaptarlo.")
    limite_bytes = settings.max_document_size_mb * 1024 * 1024
    try:
        longitud_bytes = len(contenido.encode("utf-8"))
    except UnicodeEncodeError:
        raise ErrorValidacionEntrada("DOCUMENTO_INVALIDO", "El documento contiene texto con codificación no válida.") from None
    if longitud_bytes > limite_bytes:
        raise ErrorValidacionEntrada("DOCUMENTO_DEMASIADO_GRANDE", "El documento supera el tamaño permitido.")
    if _CONTROLES_NO_PERMITIDOS.search(contenido):
        raise ErrorValidacionEntrada("DOCUMENTO_INVALIDO", "El documento contiene caracteres de control no permitidos.")


def validar_entrada_pre_llm(estado: Mapping[str, Any]) -> EntradaValidada:
    """Valida usuario y documento después de la ingesta y antes del Supervisor.

    El texto del documento se trata como material de referencia no confiable:
    aquí se valida tamaño y codificación, pero no se bloquea por mencionar
    seguridad, instrucciones o ataques.
    """
    tema = normalizar_entrada_usuario(
        estado.get("tema_pedido_chat") or "", campo="tema", maximo=MAX_LONGITUD_TEMA
    )
    if _detectar_instruccion_directa(tema):
        raise ErrorValidacionEntrada(
            "INSTRUCCION_NO_PERMITIDA",
            "La solicitud contiene una instrucción que no se puede procesar. Reformula el pedido de adaptación.",
        )
    _validar_contenido_documento(estado.get("documento_contenido"))
    titulo = normalizar_entrada_usuario(
        estado.get("documento_titulo") or "", campo="documento_titulo", maximo=300
    )
    if titulo != estado.get("documento_titulo"):
        # El contrato exige fidelidad al título de origen; no se modifica.
        if titulo != str(estado.get("documento_titulo") or "").strip():
            raise ErrorValidacionEntrada("TITULO_INVALIDO", "El título del documento contiene caracteres no permitidos.")
    if "perfil_destinatario" in estado or "formato_salida" in estado:
        # Si la interfaz ya entrega parámetros tipados, se rechazan aquí antes
        # de permitir que el Supervisor consuma una llamada para reinterpretarlos.
        validar_solicitud_adaptacion(estado)

    mensajes = estado.get("mensajes", [])
    if not isinstance(mensajes, (list, tuple)):
        raise ErrorValidacionEntrada("MENSAJE_INVALIDO", "El historial de mensajes no tiene un formato válido.")
    indice, mensaje = ultimo_mensaje_usuario(mensajes)
    if mensajes and indice is None:
        raise ErrorValidacionEntrada("MENSAJE_INVALIDO", "No hay un mensaje de usuario para clasificar.")
    if indice is not None:
        if mensaje is None:
            raise ErrorValidacionEntrada("MENSAJE_INVALIDO", "El mensaje de usuario debe ser texto plano.")
        mensaje = normalizar_entrada_usuario(mensaje, campo="mensaje", maximo=MAX_LONGITUD_MENSAJE)
        if _detectar_instruccion_directa(mensaje):
            raise ErrorValidacionEntrada(
                "INSTRUCCION_NO_PERMITIDA",
                "La solicitud contiene una instrucción que no se puede procesar. Reformula el pedido de adaptación.",
            )
    return EntradaValidada(mensaje_usuario=mensaje, tema_pedido_chat=tema)


def validar_solicitud_adaptacion(estado: Mapping[str, Any]) -> SolicitudAdaptacion:
    """Valida la clasificación del Supervisor con el contrato congelado."""
    datos = {
        campo: estado.get(campo)
        for campo in (
            "documento_titulo", "documento_contenido", "perfil_destinatario",
            "formato_salida", "nicho_sector", "nivel_detalle",
        )
        if campo in estado
    }
    try:
        solicitud = SolicitudAdaptacion.model_validate(datos)
    except ValidationError as exc:
        campos = sorted({str(error["loc"][0]) for error in exc.errors() if error.get("loc")})
        detalle = ", ".join(campos) if campos else "parámetros"
        raise ErrorValidacionEntrada(
            "SOLICITUD_INVALIDA",
            f"La solicitud no cumple el contrato de entrada ({detalle}). Revisa perfil, formato y documento.",
        ) from None
    _validar_contenido_documento(solicitud.documento_contenido)
    return solicitud


def validar_tema_consulta(tema: Any) -> str | None:
    """Limita el tema extraído antes de pasarlo al Investigador."""
    if tema is None:
        return None
    if not isinstance(tema, str):
        raise ErrorValidacionEntrada("TEMA_INVALIDO", "El tema solicitado no tiene un formato válido.")
    return normalizar_entrada_usuario(tema, campo="tema de consulta", maximo=MAX_LONGITUD_TEMA)


def validar_instruccion_modificacion(instruccion: Any) -> str:
    """Valida una instrucción puntual antes de entregarla al Modificador."""
    if not isinstance(instruccion, str):
        raise ErrorValidacionEntrada("MODIFICACION_INVALIDA", "La instrucción de modificación debe ser texto.")
    return normalizar_entrada_usuario(
        instruccion, campo="instrucción de modificación", maximo=MAX_LONGITUD_MODIFICACION
    )


def validar_objeto_fuente(objeto_id: Any) -> str:
    """Limita las lecturas del servidor MCP al prefijo de fuentes/ elegido."""
    if not isinstance(objeto_id, str) or len(objeto_id) > 1_024:
        raise ErrorValidacionEntrada("DOCUMENTO_NO_AUTORIZADO", "El documento seleccionado no es válido.")
    identificador = unicodedata.normalize("NFC", objeto_id).strip()
    if not identificador.startswith("fuentes/") or "\\" in identificador:
        raise ErrorValidacionEntrada("DOCUMENTO_NO_AUTORIZADO", "Solo se pueden leer documentos del área de fuentes.")
    segmentos = identificador[len("fuentes/"):].split("/")
    if not segmentos or any(not parte or parte in {".", ".."} for parte in segmentos):
        raise ErrorValidacionEntrada("DOCUMENTO_NO_AUTORIZADO", "El documento seleccionado no es válido.")
    if _CONTROLES_NO_PERMITIDOS.search(identificador):
        raise ErrorValidacionEntrada("DOCUMENTO_NO_AUTORIZADO", "El documento seleccionado no es válido.")
    return identificador
