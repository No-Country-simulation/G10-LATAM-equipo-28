# Seguridad de entrada, red y herramientas

Estado local de Sprint 3. Este documento describe los controles en el checkout de Sergio y las dependencias que Franklin debe revisar en OCI. No acredita despliegue, aislamiento de red ni políticas IAM aplicadas.

## Límites observados en el código

- La petición entra como `tema_pedido_chat`, mensajes de usuario y, opcionalmente, campos tipados. `validacion_entrada_inicial` comprueba esos datos antes de cualquier llamada MCP; luego el grafo busca una fuente, pide confirmación y descarga el objeto. Antes del Supervisor valida el documento y los campos tipados no nulos; comprueba la solicitud completa después de clasificar.
- `SolicitudAdaptacion` aplica Pydantic y `extra="forbid"`, pero el Redactor la construía después de que el Supervisor ya había llamado al LLM. El flujo ahora filtra texto y documento antes del Supervisor, y valida los parámetros clasificados antes del Investigador.
- Los documentos se descargan mediante MCP. El Redactor, Investigador, Revisor y Modificador reciben datos de fuente dentro de prompts que ya los delimitan como contenido no confiable. La detección de órdenes hostiles se aplica al mensaje directo del usuario; no se bloquean documentos por mencionar ataques, políticas o términos de seguridad.
- Los agentes reciben un generador estructurado, no herramientas MCP. El grafo obtiene las herramientas del servidor en nodos determinísticos. Ahora cada etapa resuelve solo su herramienta autorizada: listar fuentes, descargar una fuente o guardar la salida formateada.
- Groq se construye desde `src/seguridad/llm_client.py`; `src/llm_provider.py` conserva los proveedores configurados (Gemini, Anthropic, DeepSeek, Kimi y Ollama). El endpoint de Ollama es configurable. El acceso OCI ocurre en el proceso MCP con el SDK oficial.
- No hay en `dev` un endpoint HTTP de ingesta controlado por el usuario. Las llamadas de red de aplicación usan destinos de proveedor fijados o la configuración local de Ollama. No se instala un interceptor global.

## Validación de entrada

`src/seguridad/validadores.py` conserva el contrato existente y limita el tema a 1.000 caracteres, el mensaje de usuario a 12.000, el título al límite contractual de 300 y el documento al mínimo ya definido por `SolicitudAdaptacion` y al máximo configurado por `MAX_DOCUMENT_SIZE_MB`. Rechaza texto no válido y caracteres de control, normaliza Unicode a NFC, saltos de línea y espacios exteriores, y no devuelve valores suministrados dentro de los errores.

La heurística de prompt injection busca órdenes directas de anulación de reglas o revelación de secretos al comienzo del mensaje. Es intencionalmente estrecha: el tema de una clase, una explicación de prompt injection o un documento que cite una frase de ataque no activa el bloqueo. La clasificación del Supervisor también está delimitada en su prompt como datos de usuario. Antes del Supervisor, los enum no nulos enviados por un formulario se validan y se rechazan si son inválidos; si perfil o formato faltan o son `None`, se consideran pendientes y no se ejecuta el contrato completo todavía. Tras la clasificación, `SolicitudAdaptacion` exige perfil y formato válidos antes de continuar al Investigador. Así, los datos disponibles se rechazan pronto, pero un campo provisional no impide al Supervisor clasificar el pedido del usuario.

Las instrucciones para modificar un paquete se limitan a texto de hasta 2.000 caracteres antes de invocar al Modificador. Un objeto elegido por UI debe pertenecer al prefijo `fuentes/` y no puede contener segmentos `.` o `..`.

## Guardia de red

`src/seguridad/guardia_red.py` permite los hosts exactos usados por proveedores y los destinos previstos de Hugging Face y descarga de vocabulario de `tiktoken`; acepta Object Storage únicamente con el patrón regional `objectstorage.<region>.oraclecloud.com`. Las entradas adicionales se configuran como dominios exactos separados por coma en `NUEVAMENTE_RED_ALLOWLIST`; los comodines, credenciales en URL, esquemas distintos de HTTP/HTTPS, puertos externos no estándar y destinos locales o reservados se rechazan. Ollama solo puede usar HTTP en loopback y puerto 11434.

La fábrica de proveedores comprueba Gemini, Anthropic, DeepSeek, Kimi y Ollama; el cliente separado comprueba Groq. `validar_redireccion()` es un helper, pero los SDK de proveedor no lo tienen conectado como política de redirecciones. `validar_url_destino(..., resolver_dns=True)` permite rechazar la operación si cualquier IP resuelta no es global; los constructores actuales no activan esa opción y, aun activada, el consumidor tendría que fijar la resolución al conectar para evitar DNS rebinding. No se afirma que este código mitigue SSRF por DNS ni redirecciones. La protección actual se limita a endpoints fijos o configuración local confiable, validación de host/esquema/puerto y rechazo de direcciones IP literales ajenas a Ollama. La red de OCI la administra su SDK y tampoco pasa por esta allowlist.

## Privilegios mínimos

`src/seguridad/permisos.py` restringe las herramientas MCP del grafo por etapa. Los cinco agentes no tienen permisos de herramienta. El flujo actual no ofrece al agente escritura directa a OCI; solo el nodo Guardado conserva `guardar_resultado_formateado`.

El servidor OCI también expone herramientas de carga y escritura heredadas. La aplicación no las entrega a agentes y las etapas del grafo no pueden resolverlas por la política local. El servidor sigue compartiendo la identidad OCI del proceso MCP, por lo que las capacidades reales dependen de IAM y de dónde se ejecute ese proceso.

## Seguridad por capa

| Capa | Control local | Límite pendiente |
|---|---|---|
| Aplicación | Contrato Pydantic, límites y errores controlados | La composición UI (`app.py`) no existe en `dev`; debe llamar al grafo con la validación integrada. |
| Agente | Datos de documento delimitados como no confiables; sin herramientas MCP | Un prompt no reemplaza autorización de herramienta ni control de salida de red. |
| Herramientas | Allowlist de herramienta por etapa, incluyendo MCP | El grafo inicia el servidor MCP como subproceso por stdio; ambos comparten el contexto de ejecución local y la identidad disponible al servidor. |
| Red | Hosts exactos, esquema, puerto, loopback y helper de resolución/redirección | Se requieren reglas de egress del host o subnet para bloquear destinos fuera del proceso Python. |
| OCI/IAM | No se modificó cuenta, política, llave ni recurso externo | Franklin debe revisar la identidad, políticas del bucket y el fallback local descrito abajo. |

## Propuesta pendiente para Franklin

1. Confirmar el Dynamic Group/Instance Principal dedicado y reducir su alcance al bucket de NuevaMente y a las operaciones que requiere el flujo.
2. Confirmar si IAM puede restringir objetos por prefijo. Si no puede, conservar la validación `fuentes/` del servidor para lecturas y separar o limitar de forma equivalente las escrituras a `generados/`.
3. En `src/servidor_objeStorageOracle.py`, `_get_client()` usa Instance Principal y, ante cualquier excepción, intenta `~/.oci/config`. Conviene hacer ese fallback explícito solo para `OCI_LOCAL_DEV=1` y fallar cerrado en producción; no se cambió porque la identidad OCI/MCP pertenece a Franklin.
4. Aplicar una política de salida de red de host/subnet coherente con los hosts anteriores, acceso DNS y los endpoints legítimos activos. Auth0 debe añadirse solo con el hostname exacto del tenant cuando se integre. No se verificó una regla de firewall en esta tarea.

Antes de aplicar la propuesta, Franklin debe comprobar la sintaxis IAM vigente en la cuenta y probar por separado listar/leer `fuentes/`, escribir en `generados/formateados/` y denegar buckets u operaciones ajenos. Esta rama no contiene pruebas con credenciales OCI reales.

## Riesgos residuales

- La validación temprana ahora rechaza tema, historial y enums inválidos antes del listado MCP/OCI. La validación de tamaño y contenido del documento sigue después de la descarga, pues el texto no existe antes de seleccionar una fuente; un documento inválido puede generar una lectura OCI autorizada después de la confirmación humana, pero no una llamada LLM.
- La heurística anti-inyección reduce órdenes comunes, pero no es un clasificador semántico y puede no identificar formulaciones indirectas. Los prompts mantienen la fuente bajo un límite de confianza separado.
- La allowlist en Python no limita tráfico de otras bibliotecas o procesos ni impide DNS rebinding sin un transporte fijado. La política de egress sigue pendiente de Franklin.
- No se ejecutaron llamadas reales a LLM, Hugging Face, MCP ni OCI; las pruebas externas usan dobles.
- El `python` global del PATH no tiene las dependencias. El `.venv` local sí; sus faltantes de configuración son `GEMINI_API_KEY`, `OCI_NAMESPACE` y `~/.oci/config`. No se consultaron ni imprimieron valores secretos.

## Revisión focalizada de compatibilidad — 08/10/2026

- `SolicitudAdaptacion` mantiene perfil y formato obligatorios y no anulables. `AgentState` los declara como `Optional[str]`; por ello, antes de Supervisor puede haber ausencia o `None`, pero el flujo no los entrega al Investigador hasta completar el contrato.
- Se reprodujo que el validador anterior llamaba al contrato completo al encontrar cualquiera de las claves. Perfil solo, formato solo y una combinación explícita con `None` fallaban antes del Supervisor. La validación temprana ahora admite esos casos provisionales, sigue validando cualquier enum no nulo y aplica el contrato completo si perfil y formato ya están disponibles.
- `nicho_sector` y `nivel_detalle` tienen defaults contractuales (`General` y `Estandar`). Si el Supervisor devuelve `None`, la proyección omite esos campos para que Pydantic aplique los defaults; la validación posterior escribe los valores canónicos resultantes en `AgentState` antes del Investigador y Redactor. Los campos obligatorios perfil/formato siguen rechazando `None` al final de la clasificación.
- Si el Supervisor devuelve `None` para un valor obligatorio, o una clasificación que no satisface `SolicitudAdaptacion`, el nodo de validación corta el flujo antes del Investigador. Un fallo de salida estructurada del Supervisor también se convierte en error controlado y descarta contenido/almacenamiento residuales.
- `src/app.py` no existe en `dev`; por tanto, no hay una interfaz desplegada en este checkout que permita confirmar el payload real del formulario. La compatibilidad se probó con estados de `AgentState` representativos y el grafo compilado usando dobles para las integraciones externas.
- La guardia de red se ejecuta en las fábricas antes de construir los clientes: valida URL, host exacto, esquema y puerto; Ollama se limita a loopback en 11434. No controla la conexión efectiva, DNS resuelto, pinning de IP ni redirecciones automáticas del SDK. Groq y los proveedores configurados conservan sus endpoints fijados; Ollama sigue siendo configurable dentro de esa política local. Egress/firewall es responsabilidad de infraestructura.

## Auditoría final local — 07/10/2026

### Cambios tras la revisión adversarial

- La entrada inicial se valida antes de buscar documentos: texto obligatorio y acotado, historial estructurado, tipos/enums y formato MVP. Los objetos malformados producen errores controlados.
- La respuesta HITL exige un booleano real para confirmar y un identificador de documento de tipo texto. Respuestas como `"false"`, `1`, lista o un ID numérico no autorizan la ingesta.
- Ollama admite loopback IPv4 y IPv6 en `11434`; destinos externos siguen sujetos a HTTPS, host permitido y puerto estándar.
- El flujo válido conserva sus nodos existentes, límites de reintentos, rate limiter y contratos; no se alteró RAG ni la fidelidad.

### Matriz reproducible

| Control | Escenario y comando/prueba | Esperado | Observado | Estado | Riesgo residual |
|---|---|---|---|---|---|
| Entrada temprana | `test_entrada_invalida_se_rechaza_antes_de_listar_fuentes` (tema vacío/largo, enum inválido, tipo incorrecto, formato no implementado) | Rechazo antes de MCP/LLM | Sin invocación de herramientas ni generador | PASS | La UI debe enviar el estado conforme a `AgentState`. |
| Prompt directo | `test_inyeccion_directa_se_rechaza_sin_invocar_supervisor_ni_redactor` | Rechazar patrón directo sin búsqueda ni LLM | Rechazado antes de MCP | PASS | Heurística acotada; no es detector semántico. |
| Documento hostil | `test_documento_con_instruccion_hostil_se_conserva_como_dato_no_confiable` | No bloquear por vocabulario; mantener fuente como dato | Documento admitido por validador | PASS | Un modelo todavía puede ser influido; los agentes no tienen herramientas MCP. |
| Evasión codificada | `test_inyeccion_codificada_no_se_presenta_como_detectada_y_el_agente_sigue_sin_tools` | No afirmar detección universal; conservar agente sin tools | El texto codificado pasa como dato y la etapa del Redactor no puede resolver herramientas | LIMITADO | Puede alterar contenido generado; no concede acceso a OCI ni herramientas. Evaluar salida y mantener mínimo privilegio. |
| HITL de ejecución | `test_confirmacion_hitl_malformada_no_autoriza_ingesta` | Solo booleano `true` y objeto textual válido pueden avanzar | `"false"`, `1`, estructura nula e ID numérico son denegados | PASS | El ID textual todavía pasa por validación de prefijo antes de descarga. |
| Herramientas MCP | `tests/test_permisos.py` | Permitir solo lista/descarga/guardado en sus nodos; denegar etapas de agentes | Herramienta cruzada y agentes sin tools son rechazados | PASS | El servidor MCP conserva capacidades OCI compartidas por su identidad. |
| URL/SSRF por URL | `tests/test_guardia_red.py::test_rechaza_destinos_malformados_o_sensibles` | Rechazar hosts ajenos, credenciales, puertos y literales locales/alternativos | Rechazados; providers conocidos permitidos | PASS | Sin firewall; SDK/redirecciones no están interceptados. |
| Loopback local | `test_ollama_solo_puede_usar_loopback_en_puerto_local` | Aceptar IPv4/IPv6 loopback `11434`; rechazar LAN | Ambos loopbacks permitidos; LAN/otro puerto rechazados | PASS | La política de red del host puede ser necesaria para garantías de proceso. |
| DNS | `test_resolucion_dns_falla_cerrado_si_no_hay_resultado`, `test_resolucion_dns_rechaza_respuesta_mixta_publica_y_privada` | Si se solicita, bloquear fallos/respuestas privadas | Bloqueo probado con resolver simulado | PASS | No se activa en los SDK: no hay pinning ni protección efectiva contra rebinding. |
| Redirección | `test_redireccion_vuelve_a_aplicar_la_allowlist` | El helper rechaza siguiente destino prohibido | Helper probado; no integrado con transporte SDK | LIMITADO | La respuesta HTTP puede seguir redirects según transporte; egress externo es necesario. |
| Flujo pedagógico | `test_grafo_oficial_usa_core_adapter_ids_spec_y_limiter_compartido` | Flujo válido mantiene adaptador, IDs, revisor, guardado y límites | Prueba completa con doubles | PASS | No demuestra llamada real a LLM/MCP/OCI. |
| Contratos | `tests/test_contratos.py` | Mantener modelos y ejemplo oficial | Suite de contratos pasa | PASS | Contrato congelado sigue siendo la autoridad. |

Comandos para repetir: `.venv\\Scripts\\python.exe -m pytest -q tests/test_validadores.py tests/test_guardia_red.py tests/test_permisos.py tests/test_integracion_redactor_grafo.py tests/test_contratos.py` y `.venv\\Scripts\\python.exe -m pytest -q`.

### Hallazgos clasificados

- **CRÍTICO — ChromaDB 1.5.9 (pendiente, dependencia de la rama RAG):** `requirements.txt` fija esta versión y pip-audit encontró cuatro advisories únicos, incluido RCE pre-auth CVSS 9.3 si el endpoint afectado está expuesto y `trust_remote_code=true`; no reportó versión corregida. Además existen hallazgos de autorización multi-tenant alta. En el `dev` auditado el investigador sigue siendo stub y no hay servidor Chroma conectado; por eso no se atribuye exposición activa a este grafo. No integrar ni exponer el servidor Chroma/RBAC con estos supuestos hasta que Oscar/Franklin revisen parche, modo de ejecución y límites de red. Referencias: [PYSEC-2026-311](https://osv.dev/vulnerability/PYSEC-2026-311), [PYSEC-2026-3814](https://osv.dev/vulnerability/PYSEC-2026-3814), [PYSEC-2026-3813](https://osv.dev/vulnerability/PYSEC-2026-3813), [PYSEC-2026-3815](https://osv.dev/vulnerability/PYSEC-2026-3815).
- **ALTO — configuración IAM/OCI y red (pendiente de Franklin):** el proceso MCP comparte identidad OCI y el SDK de OCI no usa esta guardia. Limitar el Dynamic Group al bucket y operaciones requeridas; aplicar egress de host/subred y fallback local solo con `OCI_LOCAL_DEV=1`. No se cambió infraestructura.
- **MEDIO — inyección indirecta/encoded y contenido de fuente:** no existe detector universal fiable. Las fuentes están delimitadas en prompts y agentes carecen de herramientas; puede persistir influencia sobre la respuesta educativa.
- **MEDIO — redirects y DNS del SDK:** helpers no bastan para controlar solicitudes reales. Requiere transporte con redirect desactivado/revalidado y DNS fijado, o egress firewall, antes de declarar mitigación completa.
- **BAJO — instalador pip:** el escaneo inicial detectó advisories de pip 25.0.1 en el `.venv`; se actualizó localmente a pip 26.2.1 y volvió a pasar `pip check`. No se modificó un archivo del repositorio.
- **BAJO — Bandit:** siete alertas bajas preexistentes en `src`; en los archivos revisados solo permanece B110 en `src/seguridad/llm_client.py` (fallback de conteo a tokens estimados). No fue introducido por este cambio y no registra datos sensibles.
- **INFORMATIVO — herramientas:** Bandit 1.9.4 y pip-audit 2.10.1 se instalaron en un venv temporal fuera del repositorio. El escaneo actual de `.venv` reporta cinco entradas para un paquete, cuatro advisories Chroma únicos; pip quedó sin advisories conocidos. No se ejecutaron servicios externos.

### Evidencia de ejecución

- Baseline anterior: 265 pruebas aprobadas. Tras hardening: 293 pruebas aprobadas (+28), incluyendo unitarias, integración simulada del grafo y contratos.
- `.venv\\Scripts\\python.exe -m pip check`: sin dependencias rotas.
- `compileall` y `git diff --check`: limpios.
- Bandit 1.9.4 sobre `src`: siete hallazgos LOW, cero MEDIUM/HIGH. Sobre archivos de seguridad compartidos: un LOW preexistente B110 en `llm_client.py`, cero MEDIUM/HIGH.
- pip-audit 2.10.1 sobre `.venv`: 5 registros de ChromaDB 1.5.9; 4 IDs únicos, sin fix reportado. pip 25.0.1 se actualizó a 26.2.1 en `.venv`, quedando sin hallazgos pip.
- No se ejecutó Chroma, red real, LLM, MCP ni OCI en la matriz. Las afirmaciones de integración se limitan a dobles locales.
