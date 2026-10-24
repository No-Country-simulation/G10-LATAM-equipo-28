# Runbook de operación — NuevaMente

> **Qué es este documento.** Qué hacer cuando el sistema no arranca, se comporta raro o hay que
> mover una perilla. No explica qué hace NuevaMente (eso está en el README): explica cómo
> levantarlo y cómo diagnosticarlo.
>
> **Referencia:** `main` @ `346f631` (tag `v1.0.1`). Fecha: 2026-10-24.

## 1. Primero: ¿qué le falta a esta máquina?

```bash
python verificar_entorno.py
```

Dice qué falta de verdad: versión de Python, entorno virtual, dependencias, `.env`, credenciales de
OCI. Es el primer comando después de clonar, y el primero cuando algo no arranca.

## 2. Arranque local en seis pasos

```bash
# 1. Entorno virtual (obligatorio: el Python global no tiene las dependencias)
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
source .venv/bin/activate             # Linux / macOS

# 2. Dependencias
pip install -r requirements.txt

# 3. Configuración
cp .env.example .env                  # y llenar las claves

# 4. Credenciales de OCI en local
#    ~/.oci/config + llave .pem, y en .env: OCI_LOCAL_DEV=1

# 5. Verificar que todo quedó bien
python src/config.py                  # valida la configuración
python src/llm_provider.py            # construye los proveedores

# 6. Correr la app (con el venv activo)
python -m streamlit run app.py
```

> **`requirements.txt` no incluye todo.** No trae `pytest` ni las integraciones opcionales
> (`langchain-ollama`, `langchain-google-genai`, `langchain-anthropic`). Si vas a correr la suite o
> usar esos proveedores: `pip install pytest langchain-ollama langchain-google-genai langchain-anthropic`.

## 3. Tabla de síntomas

| Síntoma | Causa real | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'langgraph'` | El `streamlit` que se ejecuta es el del Python global, no el del venv | Activar el venv, o `\.venv\Scripts\python.exe -m streamlit run app.py` |
| `ImportError: DLL load failed while importing _tiktoken` | Smart App Control de Windows bloquea el binario | Seguridad de Windows → Control de aplicaciones → Smart App Control → desactivar |
| `ModuleNotFoundError: No module named 'config'` | Los módulos de `src/` se importan por nombre pelado y necesitan `src/` en `sys.path` | Correr como script (`python src/llm_provider.py`), no con `-m` |
| `FileNotFoundError: servidor_objeStorageOracle.py` | `Cliente_agemte.py` lanza el servidor por ruta relativa | Ejecutar con **cwd = `src/`** |
| Timeout al hablar con OCI en local | No hay Instance Principal fuera de la VM | `OCI_LOCAL_DEV=1` en `.env` |
| El paquete sale con `status: "exito_con_advertencias"` | OCI falló **o** la fidelidad quedó bajo el umbral | Es diseño (D-05), no un bug: leer `advertencias[]` |
| El Investigador no encuentra nada | Umbral de recuperación 0.83, consulta de una o dos palabras, o chunks muy cortos | Reformular con una consulta descriptiva (ver `docs/metricas-fidelidad.md`) |
| `FORMATO_NO_DISPONIBLE_EN_MVP` | Guion de Clase está declarado pero fuera del MVP (D-01) | Pedir otro formato |
| La corrida falla por cuota | Los tres modelos de la cadena de Groq quedaron sin cupo | Esperar el reset o cambiar `LLM_PROVIDER` |
| La app se ve en blanco pero el log avanza | Proxy o WebSocket del navegador | Probar otro navegador; el log de Streamlit dice si la corrida terminó |

## 4. Cambiar de proveedor sin tocar código

Todo se configura en `.env`; el código no se toca:

| Variable | Qué controla |
|---|---|
| `LLM_PROVIDER` | Modelo del redactor (el que más calidad necesita) |
| `VERIFIER_PROVIDER` | Modelo del verificador de fidelidad (D-02); conviene uno barato o local |
| `EMBEDDINGS_PROVIDER` | Embeddings del camino legacy (`ollama` o `gemini`) |

Valores admitidos: `gemini`, `ollama`, `deepseek`, `anthropic`, `kimi`. Los embeddings del RAG van
siempre por Hugging Face (`intfloat/multilingual-e5-base`, D-09) y se configuran aparte.

**No hay fallback entre proveedores distintos, y es a propósito** (`src/llm_provider.py:16`): si el
proveedor elegido falla, la corrida falla con un mensaje que dice cuál falló. Cambiar de proveedor
es una decisión humana de un segundo, no una ruleta automática que después nadie puede auditar.

## 5. Las perillas que cambian el comportamiento

| Variable | Por defecto | Qué pasa si la mueves |
|---|---|---|
| `FIDELIDAD_UMBRAL` | `0.80` | Sube → más regeneraciones y más `exito_con_advertencias` |
| `FIDELIDAD_MAX_REINTENTOS` | `1` | Sube → más tiempo de demo en el peor caso (D-03 acota a uno por eso) |
| `FIDELIDAD_BANDA_ALTA` / `_BAJA` | `0.85` / `0.55` | Zona donde el coseno decide sin llamar al LLM |
| `UMBRAL_RETRIEVAL` | `0.83` | Baja → el Investigador encuentra más, y también más ruido (D-12) |
| `RETRIEVAL_TOP_K` | `5` | Cuántos chunks entran al contexto |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` | Tamaño de fragmento; **obliga a reindexar** |
| `CHUNK_FUSION` / `CHUNK_MINIMO` | `300` / `100` | Higiene de fragmentos cortos; **obliga a reindexar** |
| `MAX_DOCUMENT_SIZE_MB` | `10` | Tope de subida |

> `CHUNK_SIZE`, `CHUNK_OVERLAP`, `CHUNK_FUSION` y `CHUNK_MINIMO` entran en la firma del índice: si
> los cambias y no reindexas, el índice viejo queda inconsistente con la configuración nueva.

## 6. Correr la suite

```bash
.\.venv\Scripts\python.exe -m pytest tests/ -q
# 605 passed
```

Un solo test: `python -m pytest tests/test_contratos.py::test_ejemplo_oficial_valida`.

## 7. Despliegue en la nube (Streamlit Community Cloud)

- **`requirements.txt` es el entorno.** Lo que esté instalado en tu `.venv` pero no en ese archivo
  no existe en la nube, y el error aparece solo al desplegar.
- **Las claves van en *Secrets*, no en `.env`.** Mismos nombres, otro formato.
- **No hay `~/.oci/config`.** La persistencia en OCI no está disponible en el despliegue público
  (ver `docs/limitaciones-y-alcance.md`, punto 3).

## 8. Logs

`LOG_LEVEL` en `.env` (`INFO` por defecto, `DEBUG` para diagnosticar). Un logger por módulo; los
mensajes dicen qué se intentó, con qué datos y qué falló. Los puntos donde conviene mirar primero:
ingesta (extracción de texto), recuperación (puntajes por chunk) y guardado (respuesta de OCI).

---

## Cómo verificar este documento

```bash
python verificar_entorno.py
python src/config.py
python -m pytest tests/ -q
git grep -n "OCI_LOCAL_DEV" -- src/
git grep -n "MAX_REINTENTOS_REDACTOR" -- src/grafo.py
```
