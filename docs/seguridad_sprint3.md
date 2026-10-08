# Seguridad de entrada, red y herramientas

Estado local de Sprint 3. Este documento describe los controles en el checkout de Sergio y las dependencias que Franklin debe revisar en OCI. No acredita despliegue, aislamiento de red ni políticas IAM aplicadas.

## Límites observados en el código

- La petición entra como `tema_pedido_chat` y mensajes de usuario. El grafo busca una fuente en OCI, pide confirmación, descarga el objeto y recién entonces ejecuta Validación y Supervisor.
- `SolicitudAdaptacion` aplica Pydantic y `extra="forbid"`, pero el Redactor la construía después de que el Supervisor ya había llamado al LLM. El flujo ahora filtra texto y documento antes del Supervisor, y valida los parámetros clasificados antes del Investigador.
- Los documentos se descargan mediante MCP. El Redactor, Investigador, Revisor y Modificador reciben datos de fuente dentro de prompts que ya los delimitan como contenido no confiable. La detección de órdenes hostiles se aplica al mensaje directo del usuario; no se bloquean documentos por mencionar ataques, políticas o términos de seguridad.
- Los agentes reciben un generador estructurado, no herramientas MCP. El grafo obtiene las herramientas del servidor en nodos determinísticos. Ahora cada etapa resuelve solo su herramienta autorizada: listar fuentes, descargar una fuente o guardar la salida formateada.
- Groq se construye desde `src/seguridad/llm_client.py`; `src/llm_provider.py` conserva los proveedores configurados (Gemini, Anthropic, DeepSeek, Kimi y Ollama). El endpoint de Ollama es configurable. El acceso OCI ocurre en el proceso MCP con el SDK oficial.
- No hay en `dev` un endpoint HTTP de ingesta controlado por el usuario. Las llamadas de red de aplicación usan destinos de proveedor fijados o la configuración local de Ollama. No se instala un interceptor global.

## Validación de entrada

`src/seguridad/validadores.py` conserva el contrato existente y limita el tema a 1.000 caracteres, el mensaje de usuario a 12.000, el título al límite contractual de 300 y el documento al mínimo ya definido por `SolicitudAdaptacion` y al máximo configurado por `MAX_DOCUMENT_SIZE_MB`. Rechaza texto no válido y caracteres de control, normaliza Unicode a NFC, saltos de línea y espacios exteriores, y no devuelve valores suministrados dentro de los errores.

La heurística de prompt injection busca órdenes directas de anulación de reglas o revelación de secretos al comienzo del mensaje. Es intencionalmente estrecha: el tema de una clase, una explicación de prompt injection o un documento que cite una frase de ataque no activa el bloqueo. La clasificación del Supervisor también está delimitada en su prompt como datos de usuario. Si un formulario entrega perfil o formato antes del Supervisor, Pydantic los valida antes de gastar una llamada. La salida del Supervisor y el tema que recibirá el Investigador se validan antes de la siguiente llamada LLM.

Las instrucciones para modificar un paquete se limitan a texto de hasta 2.000 caracteres antes de invocar al Modificador. Un objeto elegido por UI debe pertenecer al prefijo `fuentes/` y no puede contener segmentos `.` o `..`.

## Guardia de red

`src/seguridad/guardia_red.py` permite los hosts exactos usados por proveedores y los destinos previstos de Hugging Face y descarga de vocabulario de `tiktoken`; acepta Object Storage únicamente con el patrón regional `objectstorage.<region>.oraclecloud.com`. Las entradas adicionales se configuran como dominios exactos separados por coma en `NUEVAMENTE_RED_ALLOWLIST`; los comodines, credenciales en URL, esquemas distintos de HTTP/HTTPS, puertos externos no estándar y destinos locales o reservados se rechazan. Ollama solo puede usar HTTP en loopback y puerto 11434.

La fábrica de proveedores comprueba Gemini, Anthropic, DeepSeek, Kimi y Ollama; el cliente separado comprueba Groq. `validar_redireccion()` vuelve a evaluar cada URL redirigida si un consumidor HTTP la sigue. `validar_url_destino(..., resolver_dns=True)` permite rechazar la operación si cualquier IP resuelta no es global; el consumidor que lo use debe fijar esa misma resolución al conectar para evitar DNS rebinding. Los SDK actuales no exponen un transporte compartido que permita imponer aquí esa fijación. Este módulo es una regla de aplicación, no un firewall ni prueba que una biblioteca respete todas las redirecciones.

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

- La búsqueda del documento y su descarga ocurren antes de Validación porque el grafo actual necesita resolver y confirmar el objeto. Una entrada inválida puede provocar una operación de listado/lectura OCI, aunque se detiene antes de llamar al Supervisor, Investigador o Redactor.
- La heurística anti-inyección reduce órdenes comunes, pero no es un clasificador semántico y puede no identificar formulaciones indirectas. Los prompts mantienen la fuente bajo un límite de confianza separado.
- La allowlist en Python no limita tráfico de otras bibliotecas o procesos ni impide DNS rebinding sin un transporte fijado. La política de egress sigue pendiente de Franklin.
- No se ejecutaron llamadas reales a LLM, Hugging Face, MCP ni OCI; las pruebas externas usan dobles.
- El `python` global del PATH no tiene las dependencias. El `.venv` local sí; sus faltantes de configuración son `GEMINI_API_KEY`, `OCI_NAMESPACE` y `~/.oci/config`. No se consultaron ni imprimieron valores secretos.
