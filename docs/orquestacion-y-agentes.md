# Carril de orquestación — agentes, grafo y HITL

Mapa de integración del carril de **orquestación** (Supervisor, Investigador,
Crítico/Revisor, Modificador, grafo LangGraph y pausas HITL). Base `dev 54c1ab3`;
se completó con el PR #9 (`feature/marely-orquestacion`) y el PR #10
(`feature/marely-critico-modificador`, crítico/revisor y modificador reales).
**Estado al 19/10/2026:** `dev` = `63df7e5` (118 commits sobre `main`), con el RAG,
la ingesta y la fidelidad ya integrados. Este documento describe el estado real en
`dev` y las decisiones tomadas al integrar.

## Alcance y estado

**En `dev` hoy:**

- Contrato congelado (`src/contracts/`), `config`, `llm_provider`, `errores`.
- Acceso a OCI por MCP: `servidor_objeStorageOracle.py` + `Cliente_agemte.py`.
- `agent_state.py` (`AgentState` como `TypedDict`) y `grafo.py`.
- Agentes del carril: **Supervisor** (núcleo + nodo), **Investigador** (núcleo +
  nodo), **Crítico/Revisor** y **Modificador**. El **Redactor** (Sergio) ya está
  conectado como nodo.
- `pedagogia/`, `seguridad/` (`rate_limiter`, `llm_client`, `validadores`,
  `guardia_red`, `permisos`), `prompts/`.
- **RAG** (`src/rag/`, Oscar): chunking, embeddings e5 y Chroma. La **ingesta ya
  indexa** (descarga → indexa) y `document_id` viaja en el estado.
- **Fidelidad** (`src/fidelidad/`, Oscar): calcula `anclaje_fuente_score`. El
  Crítico/Revisor expone el puerto `CalculadorFidelidad` para inyectarlo.
- **`app.py`** (Streamlit + composition root) y el **módulo de informes** (Víctor).
- 593 pruebas en verde.

**Todavía NO:**

- **Inyectar** el calculador de `anclaje_fuente_score` en el Crítico/Revisor desde
  `app.py`. El módulo y el puerto existen; falta el cableado. Mientras no se
  inyecte, el Crítico solo aporta claridad pedagógica y observaciones.

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
| Crítico/Revisor | `agente_critico_revisor.revisar_contenido` | `critico_revisor.construir_nodo_critico_revisor(generador, calculador_fidelidad=None)` | `generador`, `calculador_fidelidad` (opcional) | `aprobado`, `evaluacion_calidad` |
| Modificador | `agente_modificador.modificar_contenido` | `modificador.construir_nodo_modificador(generador, preparar_pedagogia, obtener_solicitud)` | `generador`, `preparar_pedagogia`, `obtener_solicitud` | `contenido_adaptado`, `vueltas_modificacion`, `aprobado`, `evaluacion_calidad`, `error` |

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

- **Nodos reales**: `buscador_documentos`, `ingesta` (descarga vía MCP **e indexa
  en el RAG**), `validacion` (valida con `seguridad/validadores.py`), `supervisor`,
  `redactor_pedagogico` (Sergio), `critico_revisor`, `modificador`, `guardado_final`,
  y los HITL.
- **Nodos reales condicionados**: `investigador` usa el adaptador real **solo si
  se inyecta un `recuperador`**; si no, mantiene el stub (ver abajo). `app.py` ya
  le pasa `RecuperadorRAG()`.
- **Stubs**: ninguno en el camino principal.

### Composición (`construir_grafo`)

```python
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
- `construir_critico_revisor` y `construir_modificador`: factories
  `factory(rate_limiter) -> nodo`, mismo patrón que el Supervisor. Los defaults usan
  los núcleos reales (`critico_revisor.py`, `modificador.py`); los tests inyectan
  dobles para fijar aprobación/rechazo sin gastar cuota.
- `recuperador`: adaptador del RAG (`agentes/recuperador_rag.py`). **Si se pasa**,
  el Investigador real reemplaza al stub; si no, se conserva el stub (útil en
  pruebas que no tocan Chroma). `app.py` ya le pasa `RecuperadorRAG()`.

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
5. **Investigador real solo con `recuperador` inyectado**; el stub queda como
   default del grafo para pruebas sin Chroma. `app.py` inyecta `RecuperadorRAG()`.

## Comprobaciones

- `python -m pytest tests/ -q` → **593 pruebas** en verde (incluye
  `test_agente_supervisor`, `test_nodo_supervisor`, `test_agente_investigador`,
  `test_nodo_investigador`, `test_nodo_aclaracion`, `test_agente_critico_revisor`,
  `test_nodo_critico_revisor`, `test_agente_modificador`, `test_nodo_modificador`,
  `test_grafo_smoke`, `test_integracion_redactor_grafo`).
- Notebooks: `01` a `05`. El `05_ingesta_rag.ipynb` muestra la ingesta indexando y
  el adaptador `RecuperadorRAG`. Los de LLM real son opcionales (`LLM_PROVIDER`).
- Servicios externos (MCP, LLM) sustituidos por dobles en tests. **No** se
  corrieron llamadas reales a OCI ni smoke E2E completo.
- Entorno local: `verificar_entorno.py` reporta faltantes de máquina (Ollama,
  `.env`, `langchain-google-genai`), no del código.

## Pendientes y dependencias

- **`rag/`** — ✅ integrado (PR #17). `app.py` inyecta `RecuperadorRAG()`.
- **Fidelidad** — `src/fidelidad/` está integrado (PR #16) y el Crítico expone el
  puerto `CalculadorFidelidad`; **falta inyectarlo desde `app.py`** para que el
  `anclaje_fuente_score` se calcule en cada corrida.
- **Validación** — ✅ real (`seguridad/validadores.py`).
- **`app.py`** — ✅ existe (Streamlit + wiring de `construir_grafo`). Arranca en
  modo demo si faltan `seguridad/auth.py`, `seguridad/cuotas.py` y
  `render_documento.py`.
- **README** — ✅ actualizado (PR #19 y #21): stack real, estructura y diagrama
  fiel al grafo.
