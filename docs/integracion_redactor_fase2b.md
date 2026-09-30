# Redactor ↔ pipeline — Fase 2B (30/09/2026)

Base auditada: `dev e33a85ef60dd4bde8c379f28a7fc9f1460ce105a`.
PR #4 está merged en dev; PR #6 también. PR #3 sigue abierto, mergeable y
con `technobonal` solicitado. Este documento propone la composición para Franklin;
no cambia AgentState, grafo, proveedor, RAG, fidelidad ni contratos.

## Frontera implementada por Sergio

```python
from src.agentes.redactor import construir_nodo_redactor, enrutar_tras_redactor

nodo = construir_nodo_redactor(
    generador,             # GeneradorEstructurado, por ejemplo GeneradorLLMClient
    preparar_pedagogia,    # (PerfilDestinatario, NivelDetalle) -> spec
    obtener_solicitud,     # (Mapping[str, Any]) -> SolicitudAdaptacion validada
)
update = await nodo(state)
```

Sigue el patrón de factory con DI de `construir_nodo_supervisor` en la rama de
Marely. No importa pedagogía todavía ausente de dev ni inicializa proveedores.
El resolver de solicitud se inyecta porque AgentState no conserva el documento.
No se fabrica un documento a partir de los chunks ni se inventan IDs.

Entrada del nodo: `fuente_confirmada is True`, chunks estructurados en
`chunks_fuente_confirmados`, contador `intentos_redactor` y feedback opcional
en `evaluacion_calidad` al reintentar. El caller entrega la solicitud validada.

Chunks admitidos: mappings/modelos Pydantic con `id`+`texto` (core/investigador),
o `chunk_id`+`texto` (RAG). IDs ambiguos, repetidos o ausentes se rechazan.
Los metadatos RAG (`document_id`, `score`, `pagina`) quedan intactos en el state
original; el core recibe solamente su proyección `ChunkFuente(id, texto)`.
No filtra por score: la selección de evidencia corresponde al investigador/RAG.

Éxito: devuelve `contenido_adaptado`, `metadatos`, `intentos_redactor`,
`evaluacion_calidad=None`, `aprobado=None`, `error=None`. Metadatos usa el modelo
contractual, incluidos nicho, detalle y prerrequisitos. No declara éxito final
ni genera fidelidad/OCI. Fallo/abstención: limpia contenido, metadatos y revisión
anteriores, devuelve `status='error'`, error seguro y `aprobado=False`.
`enrutar_tras_redactor` devuelve `critico_revisor` o `error` (mapear a `END`).
El contador aumenta solo cuando se llama al generador, incluido si este falla;
no crece por preflight fallido. El nodo no realiza reintentos internos.

## Mapa de datos auditado

| Transición | Tipo/campo actual y owner | Falta o incompatibilidad | Solución mínima propuesta |
|---|---|---|---|
| Entrada → state | `SolicitudAdaptacion` en contracts (Oscar); 4 parámetros string en AgentState (Franklin) | No se conserva `documento_titulo`/`documento_contenido`; validación stub devuelve bool en `input_sanitizado: str` | Franklin conserva entrada validada; resolver entrega SolicitudAdaptacion al nodo. Definir en T2-02 origen formulario/Supervisor y ubicación de validación |
| Ingesta → state | `nodo_ingesta` descarga texto (Franklin) | Descarta texto y devuelve `estado`, clave no declarada | Guardar título/texto con campos acordados antes de RAG/redacción |
| RAG → investigador | `recuperar(document_id, consulta, ...) -> list[ChunkRecuperado]`, rama Oscar | No está en dev; DTO RAG usa `chunk_id`; Marely espera `id` y `buscar(consulta, top_k)` | Oscar/Marely acuerdan adapter del recuperador y selección; conservar ID original |
| Investigador → state | Stub: `fuente_confirmada=True`, `chunks_fuente_confirmados: list[str]` (Franklin) | Texto sin IDs no permite anchors; no document_id compartido | Franklin tipa/persiste chunks estructurados; no fabricar IDs en Redactor |
| state → spec | PR #3: `preparar_explicacion_pedagogica(perfil, nivel_detalle) -> dict` (Sergio) | Pedagogía no está aún en dev | Review/merge PR #3 por otro carril; inyectar función. Spec local, no exige canal nuevo |
| spec/chunks → Redactor | `redactar_pedagogicamente(SolicitudAdaptacion, chunks, spec, generador, feedback)` (Sergio) | Grafo usa stub, no core | Factory nueva adapta chunks/entrada y delega al core real |
| Redactor → state | ResultadoRedactor con DTO interno (Sergio) | Estudio/conceptos/prerrequisitos necesitan separarse del contenido | Nodo convierte con ContenidoAdaptado/MetadatosAprendizaje y devuelve canales existentes |
| state → siguiente | Arista incondicional a `critico_revisor` (Franklin), juez/revisor stub | Error/abstención podría alcanzar aprobación/persistencia stub | Condicional con `enrutar_tras_redactor`, ruta `error -> END`; éxito sigue al nodo existente |
| revisión → persistencia | `evaluacion_calidad`, `aprobado`, OCI (Franklin/Oscar) | Revisión es stub; Guardado usa MCP real sin validar PaqueteEducativo en grafo; falta interfaz fidelidad | No implementado aquí; owners acuerdan firma/calibración y validación del paquete |

## Cambios mínimos propuestos a Franklin — no aplicados

Estos campos son una **propuesta**, no un contrato de equipo aprobado. T2-02
todavía debe resolver identidad de documento y esquema único de chunk.

1. AgentState: conservar título/texto y document_id; sustituir `list[str]` por
   chunks estructurados. Propuesta aditiva compatible con DTO RAG actual:

   ```python
   class ChunkFuenteState(TypedDict):
       chunk_id: str
       texto: str
       score: float
       pagina: Optional[int]
       document_id: Optional[str]

   # Campos propuestos de AgentState:
   documento_titulo: Optional[str]
   documento_contenido: Optional[str]
   document_id: Optional[str]
   chunks_fuente_confirmados: Optional[list[ChunkFuenteState]]
   ```

   Si se acuerda DTO con `id`, el nodo también lo soporta. RAG e investigador
   deben conservar el mismo ID, no uno nuevo derivado por enumeración. Unificar
   `SolicitudAdaptacion.clave_cache_documento()` y RAG `calcular_document_id()`
   corresponde a T2-02/Oscar; no escoger un algoritmo aquí.
   Actualizar anotación `Metadatos` con `nicho_aplicado`,
   `nivel_detalle_aplicado`, `prerrequisitos` ya presentes en contracts.

2. Ingesta/validación/investigador: poblar esos campos tras extracción y
   validación; devolver chunks seleccionados estructurados con metadata.
   No basta cambiar la anotación: los stubs deben entregar datos reales.

3. Composición en `construir_grafo(rate_limiter=None)` tras PR #3:

   ```python
   from src.agentes.generador_llm_client import GeneradorLLMClient
   from src.agentes.redactor import construir_nodo_redactor, enrutar_tras_redactor
   from src.contracts import SolicitudAdaptacion
   from src.pedagogia.nodo import preparar_explicacion_pedagogica
   from src.seguridad.llm_client import get_llm

   def obtener_solicitud_redactor(state):
       return SolicitudAdaptacion.model_validate({
           clave: state[clave] for clave in (
               'documento_titulo', 'documento_contenido', 'perfil_destinatario',
               'formato_salida', 'nicho_sector', 'nivel_detalle',
           )
       })

   # Usar el mismo rate_limiter ya creado en construir_grafo.
   builder.add_node('redactor_pedagogico', construir_nodo_redactor(
       GeneradorLLMClient(get_llm, rate_limiter),
       preparar_explicacion_pedagogica, obtener_solicitud_redactor,
   ))
   builder.add_conditional_edges('redactor_pedagogico', enrutar_tras_redactor,
       {'critico_revisor': 'critico_revisor', 'error': END})
   ```

   Sustituye registro del stub y arista incondicional; no añadir un nodo con el
   mismo nombre dos veces. Los imports `src.*` siguen el carril Sergio/Marely;
   Franklin debe alinear imports de su módulo al componer. Supervisor tampoco
   está en dev y su factory en Marely espera generador, no RateLimiter.

4. Tests que deben pasar: `tests/test_nodo_redactor.py`, suite global, y prueba
   del grafo real con documento persistido, chunks de RAG y pedagogía real;
   una abstención/error no puede visitar revisión ni guardado. El test aislado
   de composición LangGraph ya cubre los canales actuales y la ruta a END.

## Gates restantes

- PR #3 review/merge; review del nuevo nodo; composición/producers de Franklin.
- RAG/investigador y Supervisor reales todavía en ramas de sus owners; no se
  prometió un pipeline end-to-end funcional desde el dev auditado.
- Guardado final sí invoca el MCP real; no es un stub. La revisión previa y
  la validación de PaqueteEducativo todavía no están conectadas en grafo.
- D-03: `MAX_REINTENTOS_REDACTOR=2`, con contador desde la primera generación,
  corta a las **2 generaciones totales**. Confirmar en demo si se desean
  1 inicial + 2 reintentos = 3 intentos. No se cambió esa lógica.
- Revisor/Modificador: no iniciados. Confirmar ownership, interfaz con fidelidad.
- Proyecto: 5 formatos; contrato actual: 4. Guion espera schema T1-02; los cuatro
  actuales pueden integrarse sin esperar ese quinto formato.
- Discord exige login en esta sesión. No se asegura ausencia de respuestas allí;
  respuesta a Franklin queda en borrador, sin duplicar mensajes/daily.
