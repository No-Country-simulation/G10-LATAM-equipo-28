"""Carga y valida las fichas pedagógicas versionadas por formato."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.contracts import FORMATOS_IMPLEMENTADOS_MVP, FormatoSalida, MODELO_ITEM_POR_FORMATO

_CLAVES_FICHA = {
    "version",
    "formato",
    "nombre",
    "campos_obligatorios",
    "campos_opcionales",
    "reglas",
    "fuente",
}


@dataclass(frozen=True)
class FormatoPedagogico:
    """Metadatos pedagógicos sin lógica de generación ni esquema duplicado."""

    version: str
    formato: FormatoSalida
    nombre: str
    campos_obligatorios: tuple[str, ...]
    campos_opcionales: tuple[str, ...]
    reglas: tuple[str, ...]
    fuente: str


def _texto_no_vacio(dato: dict[str, Any], clave: str, archivo: Path) -> str:
    valor = dato.get(clave)
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{archivo.name}: '{clave}' debe ser texto no vacío.")
    return valor


def _lista_textos(dato: dict[str, Any], clave: str, archivo: Path) -> tuple[str, ...]:
    valor = dato.get(clave)
    if not isinstance(valor, list) or any(
        not isinstance(item, str) or not item.strip() for item in valor
    ):
        raise ValueError(f"{archivo.name}: '{clave}' debe ser una lista de textos no vacíos.")
    if len(valor) != len(set(valor)):
        raise ValueError(f"{archivo.name}: '{clave}' no puede repetir valores.")
    return tuple(valor)


def _cargar_ficha(archivo: Path) -> FormatoPedagogico:
    try:
        dato = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo cargar {archivo.name}: {exc}") from exc
    if not isinstance(dato, dict):
        raise ValueError(f"{archivo.name}: la raíz debe ser un objeto JSON.")

    desconocidas = set(dato) - _CLAVES_FICHA
    faltantes = _CLAVES_FICHA - set(dato)
    if desconocidas:
        raise ValueError(f"{archivo.name}: claves desconocidas: {sorted(desconocidas)}.")
    if faltantes:
        raise ValueError(f"{archivo.name}: faltan claves: {sorted(faltantes)}.")

    nombre = _texto_no_vacio(dato, "nombre", archivo)
    version = _texto_no_vacio(dato, "version", archivo)
    fuente = _texto_no_vacio(dato, "fuente", archivo)
    try:
        formato = FormatoSalida(_texto_no_vacio(dato, "formato", archivo))
    except ValueError as exc:
        raise ValueError(f"{archivo.name}: formato no reconocido.") from exc
    if formato not in FORMATOS_IMPLEMENTADOS_MVP:
        raise ValueError(f"{archivo.name}: {formato.value} no está habilitado en el MVP.")

    requeridos = _lista_textos(dato, "campos_obligatorios", archivo)
    opcionales = _lista_textos(dato, "campos_opcionales", archivo)
    reglas = _lista_textos(dato, "reglas", archivo)
    if set(requeridos) & set(opcionales):
        raise ValueError(f"{archivo.name}: campos obligatorios y opcionales se superponen.")

    modelo = MODELO_ITEM_POR_FORMATO[formato]
    campos_modelo = set(modelo.model_fields)
    campos_ficha = set(requeridos) | set(opcionales)
    if campos_ficha != campos_modelo:
        faltan = campos_modelo - campos_ficha
        sobran = campos_ficha - campos_modelo
        raise ValueError(
            f"{archivo.name}: campos no corresponden con {modelo.__name__}; "
            f"faltan={sorted(faltan)}, sobran={sorted(sobran)}."
        )

    return FormatoPedagogico(
        version=version,
        formato=formato,
        nombre=nombre,
        campos_obligatorios=requeridos,
        campos_opcionales=opcionales,
        reglas=reglas,
        fuente=fuente,
    )


def cargar_formatos_pedagogicos(
    directorio: Path | None = None,
) -> dict[FormatoSalida, FormatoPedagogico]:
    """Carga las cuatro fichas habilitadas y verifica que no cambien el contrato."""
    ruta = directorio or Path(__file__).resolve().parent / "formatos"
    if not ruta.is_dir():
        raise ValueError(f"No existe el directorio de formatos pedagógicos: {ruta}.")

    fichas: dict[FormatoSalida, FormatoPedagogico] = {}
    for archivo in sorted(ruta.glob("*.json")):
        ficha = _cargar_ficha(archivo)
        if ficha.formato in fichas:
            raise ValueError(f"Hay más de una ficha para {ficha.formato.value}.")
        fichas[ficha.formato] = ficha

    esperados = set(FORMATOS_IMPLEMENTADOS_MVP)
    if set(fichas) != esperados:
        faltan = sorted(formato.value for formato in esperados - set(fichas))
        sobran = sorted(formato.value for formato in set(fichas) - esperados)
        raise ValueError(f"Catálogo incompleto: faltan={faltan}, sobran={sobran}.")
    return fichas
