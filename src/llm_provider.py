"""
NuevaMente — Fábrica de proveedores de LLM y embeddings.

ESTE ES EL ÚNICO ARCHIVO DEL PROYECTO QUE NOMBRA PROVEEDORES CONCRETOS.

El resto del código pide `get_llm()` y no sabe —ni debe saber— si detrás hay
Gemini, Ollama o DeepSeek. Cambiar de proveedor es cambiar una línea del .env.

    get_llm()           → LLM redactor      (LLM_PROVIDER)
    get_verifier_llm()  → LLM verificador   (VERIFIER_PROVIDER)   [decisión D-02]
    get_embeddings()    → Embeddings        (EMBEDDINGS_PROVIDER)

------------------------------------------------------------------------------
NOTA SOBRE FALLBACK  (decisión del Decision Gate §2.6)

No hay fallback automático entre proveedores. A propósito.

Un fallback automático esconde el problema: el sistema "funciona" mientras
consume cuota de pago sin que nadie se entere, y la causa real queda enterrada.
Aquí, si un proveedor falla, falla rápido y el mensaje dice CUÁL falló y QUÉ
hacer. Cambiar de proveedor es una decisión humana de un segundo.

------------------------------------------------------------------------------
⚠ IDENTIFICADORES DE MODELO

Los defaults de abajo son PUNTOS DE PARTIDA, no verdad verificada. Los catálogos
de modelos cambian cada pocas semanas. Antes de usar un proveedor:

  1. Verificar el identificador exacto en su documentación oficial.
  2. Verificar los límites de su capa gratuita.
  3. Anotar ambos en el README, con la fecha de consulta.

Si un identificador está mal, se corrige en el .env sin tocar este archivo.
------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any

from config import ConfigError, settings

# =============================================================================
# Modelos por defecto — VERIFICAR antes de usar (ver nota de arriba)
# =============================================================================

DEFAULT_CHAT_MODEL: dict[str, str] = {
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.1:8b",
    "deepseek": "deepseek-chat",
    "anthropic": "claude-sonnet-4-20250514",
    "kimi": "moonshot-v1-8k",
}

DEFAULT_EMBEDDINGS_MODEL: dict[str, str] = {
    "ollama": "nomic-embed-text",
    "gemini": "models/text-embedding-004",
}

# Proveedores compatibles con la API de OpenAI: se construyen igual,
# sólo cambia la URL base y la clave.
OPENAI_COMPATIBLE_BASE_URL: dict[str, str] = {
    "deepseek": "https://api.deepseek.com/v1",
    "kimi": "https://api.moonshot.cn/v1",
}


class ProviderError(RuntimeError):
    """Fallo al construir un proveedor, con instrucciones de arreglo."""


def _falta_dependencia(paquete: str, proveedor: str) -> ProviderError:
    return ProviderError(
        f"\n\nFalta el paquete '{paquete}', necesario para el proveedor "
        f"'{proveedor}'.\n"
        f"Instalalo con:  pip install {paquete}\n"
        f"O cambiá de proveedor en el .env.\n"
    )


# =============================================================================
# Constructores de chat
# =============================================================================


def _build_chat(provider: str, model: str, temperature: float) -> Any:
    """Construye un modelo de chat para el proveedor dado."""

    if provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise _falta_dependencia("langchain-google-genai", provider) from None
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=settings.api_key_for("gemini"),
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise _falta_dependencia("langchain-ollama", provider) from None
        return ChatOllama(
            model=model,
            temperature=temperature,
            base_url=settings.ollama_base_url,
        )

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise _falta_dependencia("langchain-anthropic", provider) from None
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            anthropic_api_key=settings.api_key_for("anthropic"),
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    if provider in OPENAI_COMPATIBLE_BASE_URL:
        # DeepSeek y Kimi exponen una API compatible con OpenAI.
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise _falta_dependencia("langchain-openai", provider) from None
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=settings.api_key_for(provider),
            base_url=OPENAI_COMPATIBLE_BASE_URL[provider],
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    raise ConfigError(
        f"Proveedor de chat desconocido: {provider!r}. "
        f"Opciones: {', '.join(sorted(DEFAULT_CHAT_MODEL))}"
    )


# =============================================================================
# API pública
# =============================================================================


def get_llm() -> Any:
    """LLM redactor. Lee LLM_PROVIDER / LLM_MODEL / LLM_TEMPERATURE."""
    provider = settings.llm_provider
    model = settings.llm_model or DEFAULT_CHAT_MODEL.get(provider, "")
    if not model:
        raise ConfigError(
            f"No hay modelo por defecto para {provider!r}. Definí LLM_MODEL en el .env."
        )
    return _build_chat(provider, model, settings.llm_temperature)


def get_verifier_llm() -> Any:
    """
    LLM verificador de fidelidad (decisión D-02).

    Se construye por separado, a propósito: su tarea —clasificar afirmaciones
    contra los chunks— es mucho más simple que redactar, y puede correr en un
    modelo más barato o local. Ponerlo en el mismo modelo caro que el redactor
    es desperdiciar cuota.

    Temperatura 0 por defecto: la verificación debe ser determinista.
    """
    provider = settings.verifier_provider
    model = settings.verifier_model or DEFAULT_CHAT_MODEL.get(provider, "")
    if not model:
        raise ConfigError(
            f"No hay modelo por defecto para {provider!r}. Definí VERIFIER_MODEL en el .env."
        )
    return _build_chat(provider, model, settings.verifier_temperature)


def get_embeddings() -> Any:
    """
    Modelo de embeddings.

    ⚠ Es el que más llamadas hace: UNA POR CHUNK. Dejarlo en Ollama local
    evita gastar la cuota gratuita del LLM en vectorizar texto, y saca la
    indexación de la dependencia de red — lo cual también protege la demo.
    """
    provider = settings.embeddings_provider
    model = settings.embeddings_model or DEFAULT_EMBEDDINGS_MODEL.get(provider, "")
    if not model:
        raise ConfigError(
            f"No hay modelo de embeddings por defecto para {provider!r}. "
            f"Definí EMBEDDINGS_MODEL en el .env."
        )

    if provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError:
            raise _falta_dependencia("langchain-ollama", provider) from None
        return OllamaEmbeddings(model=model, base_url=settings.ollama_base_url)

    if provider == "gemini":
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError:
            raise _falta_dependencia("langchain-google-genai", provider) from None
        return GoogleGenerativeAIEmbeddings(
            model=model, google_api_key=settings.api_key_for("gemini")
        )

    raise ConfigError(
        f"Proveedor de embeddings desconocido: {provider!r}. "
        f"Opciones: {', '.join(sorted(DEFAULT_EMBEDDINGS_MODEL))}"
    )


# =============================================================================
# Diagnóstico:  python llm_provider.py
# =============================================================================

if __name__ == "__main__":
    print("Verificando configuración de proveedores...\n")
    try:
        settings.validate()
    except ConfigError as exc:
        print(f"❌ {exc}")
        raise SystemExit(1)

    print(f"   {settings.resumen_seguro()}\n")

    for etiqueta, constructor in (
        ("LLM redactor", get_llm),
        ("LLM verificador", get_verifier_llm),
        ("Embeddings", get_embeddings),
    ):
        try:
            constructor()
            print(f"✅ {etiqueta}: construido correctamente")
        except (ConfigError, ProviderError) as exc:
            print(f"❌ {etiqueta}: {exc}")

    print(
        "\nNota: esto verifica que los clientes se construyen, no que las claves "
        "sean válidas.\nPara eso hay que hacer una llamada real."
    )
