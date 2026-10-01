# Carril de orquestación — agentes, grafo y HITL

Mapa de integración del carril de **orquestación** (Supervisor, Investigador, grafo
LangGraph y pausas HITL). Base `dev 54c1ab3`; se completa con el PR #9
(`feature/marely-orquestacion`). Este documento describe el estado real en `dev`
y las decisiones tomadas al integrar, para que Franklin (integración) y el
Investigador/Verificador reales se conecten sin adivinar.

## Alcance y estado

**En `dev` hoy:**

- Contrato congelado (`src/contracts/`), `config`, `llm_provider`, `errores`.
- Acceso a OCI por MCP: `servidor_objeStorageOracle.py` + `Cliente_agemte.py`.
- `agent_state.py` (`AgentState` como `TypedDict`) y `grafo.py`.
- Agentes del carril: **Supervisor** (núcleo + nodo) e **Investigador** (núcleo +
  nodo). El **Redactor** (Sergio) ya está conectado como nodo.
- `pedagogia/`, `seguridad/` (rate limiter, `llm_client` de Franklin), `prompts/`.
- 186 pruebas en verde.

**Todavía NO:**

- `rag/` (Chroma) — carril de Oscar. Sin esto no hay `recuperador` real.
- Verificador / `anclaje_fuente_score` — ver "Pendientes".
- `app.py` (composition root + Streamlit).
- Crítico/Revisor, Modificador y Validación reales (siguen stub).

## Patrón de agente (Decisión A3)

Cada agente es un **núcleo puro `async`** que recibe sus dependencias
**inyectadas** y devuelve resultados tipados. No instancia el cliente LLM ni
nombra proveedor. El adaptador de nodo es una capa fina que traduce
`estado → estado`.

Protocolos compartidos (`src/agentes/protocolos.py`): `GeneradorEstructurado`
(`async generate(*, prompt, output_model)`). El Investigador además exige un
`Recuperador` (`buscar(consulta, top_k) -> list[ChunkConScore]`).

| Agente | Núcleo puro | Adaptador de nodo | Dependencias inyectadas | Claves que escribe al estado |
|---|---|---|---|---|
| Supervisor | `agente_supervisor.clasificar_intencion` | `supervisor.construir_nodo_supervisor(generador)` | `generador` | `tema_consulta`, `perfil_destinatario`, `formato_salida`, `nicho_sector`, `nivel_detalle` |
| Investigador | `agente_investigador.investigar` | `investigador.construir_nodo_investigador(recuperador, generador)` | `recuperador`, `generador` | `fuente_confirmada`, `chunks_fuente_confirmados`, `chunks_fuente_estructurados`, `mensaje_aclaracion` |
| Redactor (Sergio) | `agente_redactor_pedagogico.redactar_pedagogicamente` | `redactor.construir_nodo_redactor(generador, preparar_pedagogia, obtener_solicitud)` | `generador`, `preparar_pedagogia`, `obtener_solicitud` | `contenido_adaptado`, `metadatos`, `intentos_redactor`, `evaluacion_calidad`, `aprobado`, `error` |

Detalles que importan:

- El Supervisor serializa los enums a su **forma canónica corta** (`"Principiante"`)
  y usa `tema_pedido_chat` como default solo si el modelo no extrajo
  `tema_consulta` (los campos siguen siendo independientes).
- El Investigador escribe el **canal aditivo** `chunks_fuente_estructurados`
  (`{"id", "texto", "score"}`) que consume el Redactor. Un fallo o abstención
  deja ese canal en `[]` para no revivir evidencia de una corrida anterior.
- `GeneradorLLMClient` (`src/agentes/generador_llm_client.py`) adapta
  `get_llm(...).with_structured_output(...).invoke(...)` al protocolo, con
  `max_tokens=4096`. `GeneradorLangchain` envuelve cualquier chat model de
  LangChain (usado en los notebooks con LLM real).

## El grafo

Flujo (nodos reales, stubs y HITL):

```
buscador_documentos -> confirmar_ejecucion (HITL) -> ingesta -> validacion
-> supervisor -> investigador
     ├─ match      -> redactor_pedagogico -> critico_revisor -> ...
     └─ aclaracion -> nodo_aclaracion (HITL, 1 ronda) -> END
critico_revisor -> guardado_final -> confirmar_modificacion (HITL)
                -> modificador -> critico_revisor -> ...
```

- **Nodos reales**: `buscador_documentos`, `ingesta` (descarga vía MCP), `supervisor`,
  `redactor_pedagogico` (Sergio), `guardado_final`, y los HITL.
- **Nodos reales condicionados**: `investigador` usa el adaptador real **solo si
  se inyecta un `recuperador`**; si no, mantiene el stub (ver abajo).
- **Stubs**: `validacion`, `critico_revisor`, `modificador`.

### Composición (`construir_grafo`)

```python
async def construir_grafo(
    rate_limiter: RateLimiter | None = None,
    *,
    preparar_pedagogia=None,
    get_llm_factory=None,
    construir_supervisor=None,
    recuperador=None,
):
```

- `rate_limiter`: compartido por los nodos con LLM (Supervisor y Redactor). Si no
  se pasa, se crea uno nuevo (útil en scripts; en `app.py` conviene una instancia
  única y reusarla entre reruns).
- `get_llm_factory`: `get_llm` oficial; permite probar sin llamadas externas.
- `construir_supervisor`: `factory(rate_limiter) -> nodo`. **Ojo con la asimetría**:
  el núcleo `construir_nodo_supervisor` recibe un **generador**, no un limiter. El
  default del grafo envuelve correctamente:
  `construir_nodo_supervisor(GeneradorLLMClient(get_llm_factory, rate_limiter))`.
  (Corrige el default original de la integración, que pasaba el limiter directo.)
- `recuperador`: vector store (`rag/vectorstore.py`). **Si se pasa**, el nodo
  Investigador real reemplaza al stub; si no, se conserva el stub. Hoy `rag/` no
  está en `dev`, así que el default es el stub.

### Invariante del stub de Investigador

El stub confirma la fuente con un chunk de texto **sin ID** (`"[STUB] ..."`). Eso
es a propósito: sin RAG no se inventan `chunk_id` reales, y el Redactor rechaza
textos sin ID, por lo que una corrida sin recuperador **no genera ni persiste**.
Los tests lo fijan (`test_investigador_stub_no_genera_ni_persiste_ids_inventados`).

## HITL (interrupts)

| Nodo | Expone (`interrupt`) | Espera al `Command(resume=...)` |
|---|---|---|
| `confirmar_ejecucion` | `candidatos_documento`, `objeto_id_confirmado` | `{"confirmado": bool, "objeto_id_confirmado": str o None}` |
| `confirmar_modificacion` | `vueltas_modificacion` | `{"instruccion": str o None}` |
| `nodo_aclaracion` | `tipo="aclaracion"`, `mensaje_aclaracion` | `{"respuesta": str o None}` |

**Decisión — aclaración informativa de 1 ronda.** Cuando el Investigador no
confirma cobertura (`fuente_confirmada=False`), el grafo entra a `nodo_aclaracion`:
pausa, expone `mensaje_aclaracion` y guarda `respuesta_aclaracion_usuario`. Luego
**termina** (`END`). `app.py` decide si reinicia con otro tema o pide subir otro
documento. Se eligió así porque la spec habla de "1 ronda HITL" y no especifica un
bucle de reinicio; es extensible a "re-investigar 1 vez" sin tocar el agente.

## Contadores

`intentos_redactor` (tope 2) y `vueltas_modificacion` (tope 5) **se incrementan
sobre el valor existente, nunca se resetean**. El Redactor solo incrementa
`intentos_redactor` cuando realmente llama al generador.

## Decisiones registradas

1. **Decisión A3** — el grafo no elige proveedor ni rate limiter; todo entra por
   inyección desde `app.py`. Los agentes no instancian el cliente LLM.
2. **Imports `src.`-prefijados en `grafo.py`** — el smoke test
   (`test_grafo_smoke.py`) protege contra el import pelado que dejó `main` roto.
3. **Aclaración informativa de 1 ronda** (arriba).
4. **Fix del default de Supervisor** en `construir_grafo` (arriba).
5. **Investigador real solo con `recuperador` inyectado**; stub por defecto
   mientras `rag/` no esté en `dev`.

## Comprobaciones

- `python -m pytest tests/ -q` → **186 pruebas** en verde (incluye
  `test_agente_supervisor`, `test_nodo_supervisor`, `test_agente_investigador`,
  `test_nodo_investigador`, `test_nodo_aclaracion`, `test_grafo_smoke`,
  `test_integracion_redactor_grafo`).
- Notebooks: `notebooks/01_supervisor_intencion.ipynb` y
  `notebooks/02_investigador_cobertura.ipynb` (con generador/recuperador
  inyectados; opcionales con LLM real si hay `LLM_PROVIDER`).
- Servicios externos (MCP, LLM) sustituidos por dobles en tests. **No** se
  corrieron llamadas reales a OCI ni smoke E2E completo.
- Entorno local: `verificar_entorno.py` reporta faltantes de máquina (Ollama,
  `.env`, `langchain-google-genai`), no del código.

## Pendientes y dependencias

- **`rag/` (Oscar, `feature/oscar-rag`)**: habilita un `recuperador` real →
  `construir_grafo(..., recuperador=...)` enciende el Investigador real.
- **Verificador / `anclaje_fuente_score` (coordinar con Oscar,
  `feature/oscar-calidad`)**: `feature/oscar-calidad` ya trae "cascada de coseno +
  juez LLM". Definir quién cierra el nodo Crítico/Revisor real para no duplicar.
- **Crítico/Revisor, Modificador, Validación**: stubs; definir owners.
- **`app.py`**: composition root (Streamlit + wiring de `construir_grafo`).
- **README**: su tabla "Estado" y su sección "Estructura" quedaron desactualizadas
  frente al código real (`src/grafo.py` + `src/agentes/`, no `src/orquestacion/`).
