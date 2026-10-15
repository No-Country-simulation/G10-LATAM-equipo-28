# Redactor conectado al pipeline — Fase 2C

Integración coordinada con el owner del grafo/AgentState en el mismo PR #7,
base `dev e33a85e`. Este documento describe la implementación actual y
supersede la propuesta de Fase 2B. PR #4 y #6 están merged; PR #3 sigue abierto.

## Cambios de integración

- `AgentState` conserva `chunks_fuente_confirmados: Optional[list[str]]`.
  Añade tres canales `NotRequired` (Python 3.11+): `documento_titulo`,
  `documento_contenido`, `chunks_fuente_estructurados`.
- El canal nuevo contiene diccionarios serializados del DTO existente:
  `ChunkRecuperado.model_dump()`; admite también `id`/`texto` del Investigador.
  No se crea otro DTO ni se inventan `document_id` o IDs de chunks.
- Ingesta conserva `nombre` y `texto_extraido` de `descargar_documento`.
  Reinicia el canal estructurado y la confirmación de fuente en cada ingesta,
  para que el productor confirme evidencia del documento actual.
- `Metadatos` incorpora los campos ya devueltos por el contrato vigente:
  `nicho_aplicado`, `nivel_detalle_aplicado`, `prerrequisitos`.
- `obtener_solicitud_redactor(state)` valida título/texto, perfil y formato con
  `SolicitudAdaptacion`. Nicho/detalle ausentes usan sus defaults oficiales.
  No reconstruye un documento desde el chat, el tema ni los chunks.
- El grafo elimina el stub del Redactor y registra `construir_nodo_redactor`
  con `GeneradorLLMClient(get_llm_factory, rate_limiter)`, resolución de solicitud
  y pedagogía inyectada. El adapter mantiene `max_tokens=4096`.
- Una arista condicional usa `enrutar_tras_redactor`: generación válida sigue
  a `critico_revisor`; error o abstención termina en `END`, sin guardado.
- Error/abstención elimina contenido, metadatos y revisión anteriores y devuelve
  error seguro. El contador aumenta solo al llamar al generador.

## Datos y composición

| Transición | Campo o interfaz real | Responsable / límite |
|---|---|---|
| Descarga → state | `nombre` → `documento_titulo`; `texto_extraido` → `documento_contenido` | Ingesta conectada, sin implementar indexación |
| Supervisor → solicitud | `perfil_destinatario`, `formato_salida`, `nicho_sector`, `nivel_detalle` | Interfaz actual conservada; Supervisor no está en dev |
| RAG/Investigador → state | `fuente_confirmada=True`; `chunks_fuente_estructurados=[chunk.model_dump(), ...]` | El productor debe publicar evidencia actual; RAG no está en dev |
| State → Redactor | Solicitud validada; proyección `chunk_id/id` → `ChunkFuente.id`, `texto` | Nodo existente de Sergio; rechaza IDs ambiguos/repetidos/ausentes |
| Perfil/detalle → spec | `preparar_explicacion_pedagogica(perfil, nivel_detalle)` | Función oficial de PR #3, inyectable mientras esté pendiente |
| Core → state | `contenido_adaptado`, `metadatos`, contador, limpieza de revisión/error | Modelos oficiales; anchors conservan los IDs recibidos |
| State → siguiente | `critico_revisor` / `END` | Orden existente; Revisor y Modificador siguen stub |

Ejemplo de evidencia, sin valores fabricados por el Redactor:

```python
update_investigador = {
    "fuente_confirmada": True,
    "chunks_fuente_estructurados": [chunk.model_dump() for chunk in recuperados],
}
```

Los metadatos RAG (`score`, `pagina`, `document_id`, si existen) permanecen en
el canal nuevo para otros consumidores. El core recibe solo ID y texto.
El Redactor no decide cobertura ni aplica otro umbral de retrieval.
Si el canal nuevo está presente, incluso vacío/None, prevalece sobre el legacy.
El fallback legacy solo mantiene compatibilidad con callers aislados de Fase 2B
cuando el canal nuevo no existe. Los textos legacy sin ID se rechazan.

```python
pipeline = await construir_grafo(
    rate_limiter_compartido,
    preparar_pedagogia=preparar_explicacion_pedagogica,
    get_llm_factory=get_llm,
    construir_supervisor=factory_supervisor,  # firma actual: (rate_limiter) -> nodo
)
```

La factory del grafo recibe el mismo limiter que Redactor. El core de Supervisor
de la rama de Marely recibe un generador, no un limiter: su futura composición
puede envolver `construir_nodo_supervisor(GeneradorLLMClient(get_llm, limiter))`.
No se cambió esa API ajena ni se copió su implementación. La carga por defecto
conserva la llamada histórica `construir_nodo_supervisor(rate_limiter)`; Franklin
coordina ese punto con Marely al integrar su rama.

Sin inyección se importan pedagogía y get_llm oficiales de forma diferida.
No hay mapping pedagógico alternativo ni Supervisor ficticio como fallback.
Como PR #3 y Supervisor no están en dev, la construcción sin esas dependencias
no está disponible todavía. El Investigador stub permanece: su texto sin IDs
no genera ni se guarda; la indexación/recuperación real sigue pendiente del equipo.

## Comprobaciones

- 78 tests dirigidos: AgentState/checkpoint, grafo compilado y HITL reales,
  core y adapter; MCP y LLM sustituidos solo por dobles en tests.
- 116 tests globales; `pip check` y `git diff --check` limpios.
- Árbol temporal con PR #3: 140 tests; además los cuatro formatos PASS con
  grafo actualizado, pedagogía real y DTO `ChunkRecuperado` LIVE serializado.
- Se prueban los cuatro formatos, anchors originales, spec, solicitud,
  errores/abstenciones sin residuales, no guardado inválido, una sola instancia
  de limiter y factory compartida, ingesta que invalida evidencia anterior.
- La semántica actual sigue siendo dos generaciones totales. No se cambió D-03;
  la demo debe decidir si desea inicial + dos reintentos = tres intentos.
- No se hicieron llamadas reales Groq/OCI ni se repitió el smoke histórico PASS.

## Review y dependencias

Franklin debe revisar los tres canales aditivos, invalidación en ingesta,
publicación del canal estructurado por el productor, composición/DI, ruta END
antes de guardado y compatibilidad del contador. PR #7 no se mergea unilateralmente.

Pendientes externos: review/merge PR #7 y PR #3; integración real del productor
RAG/Investigador y Supervisor; fidelidad/revisión y validación final del paquete
según sus owners. El contrato habilita cuatro formatos; Guion espera T1-02.
No se modificaron contracts, RAG, fidelidad, llm_client ni RateLimiter; no se
iniciaron Revisor o Modificador. No se sincronizó la rama porque dev no avanzó.
