# NuevaMente — Especificación Funcional del Producto

**Proyecto:** NuevaMente — Sistema Inteligente de Adaptación y Generación de Contenido Educativo
**Contexto:** Hackathon ONE G10 — Oracle Next Education & Alura · Programa ONE Grupo 10
**Documento fuente:** *Proyecto 1 – NuevaMente* (7 páginas) — **única fuente de verdad** de esta especificación
**Fase:** 1 de N — Definición Funcional · **NO incluye arquitectura ni selección tecnológica**
**Fecha:** 2026-09-15
**Estado:** Borrador para aprobación del equipo (ver `DECISION GATE` al final)

---

## 0. Cómo leer este documento

### 0.1 Convención de trazabilidad (obligatoria)

Cada afirmación de este documento lleva una etiqueta de origen. **Nada aquí es invención.**

| Etiqueta | Significado | Regla de uso |
|---|---|---|
| `[EXP]` | **Requisito explícito.** Está escrito literalmente en el documento fuente. Se cita la página. | No es negociable sin cambiar el alcance del Hackathon. |
| `[INF]` | **Inferencia necesaria.** No está escrito, pero es *imprescindible* para implementar un `[EXP]`. | Requiere confirmación del equipo, pero su ausencia rompe un `[EXP]`. |
| `[PROP]` | **Propuesta opcional.** Ni explícito ni necesario. Se incluye sólo como opción evaluable. | Se descarta por defecto. Entra sólo por decisión explícita. |
| `[AMB]` | **Ambigüedad detectada.** El documento se contradice, omite o es interpretable de más de una forma. | **Bloquea** decisiones de diseño hasta resolverse. Ver §11. |

Las referencias de página se escriben `(p.4)`.

### 0.2 Reglas que rigen esta fase

1. No se escribe código.
2. No se proponen tecnologías concretas. **Excepción:** cuando el documento fuente *impone* una tecnología, ésta se reporta como **restricción de producto**, no como propuesta del autor. Sólo hay una: **OCI Object Storage, capa Always Free** `[EXP] (p.2, p.4, p.6)`. Las demás tecnologías que el documento menciona (LangChain, Chroma, FAISS, PyPDF, Streamlit, Gradio, Pydantic) aparecen en el documento como **sugerencias explícitamente no vinculantes** y se registran en §11 como decisiones abiertas, no como decisiones tomadas.
3. No se diseña arquitectura.
4. No se agregan funcionalidades por interés técnico.
5. Toda ambigüedad se marca `[AMB]` y escala a §11 Open Questions.
6. El MVP prioriza el **Checklist de Evaluación** del Hackathon `(p.5-6)` por encima de cualquier otra consideración.

### 0.3 Hallazgo crítico sobre la prioridad del MVP

El documento contiene **tres listas de obligatoriedad distintas** que no son idénticas entre sí:

- **Objetivo del Hackathon** — 6 puntos `(p.3)`
- **Resultados esperados** — 4 bloques con sub-ítems `(p.3-4)`
- **Requisitos mínimos (Checklist de Evaluación)** — 8 casillas `(p.5-6)`

**Decisión de esta especificación:** el **Checklist de Evaluación `(p.5-6)` es la autoridad final** porque es el instrumento declarado de evaluación ("Requisitos mínimos (Checklist de Evaluación)"). Los otros dos se tratan como fuentes complementarias que **añaden** requisitos, nunca como fuentes que los relajan. La §9 (Matriz de Trazabilidad) está construida sobre el Checklist y auditada contra las otras dos listas.

---

## 1. Product Vision

### 1.1 Qué es NuevaMente

NuevaMente es un **sistema de adaptación y generación de contenido educativo** que ingiere documentación técnica densa (PDF, Markdown o texto) y la transforma automáticamente en **paquetes educativos personalizados y estructurados**, parametrizados por perfil del destinatario, formato pedagógico y nicho de aplicación, usando RAG para anclar cada afirmación en el material original. `[EXP] (p.1)`

### 1.2 Para quién es

**Sector:** EdTech / Capacitación Corporativa / Plataformas de Educación Técnica. `[EXP] (p.1)`

**Clientes:** instituciones educativas, empresas de tecnología y equipos de ingeniería que necesitan capacitar públicos diversos —desde principiantes en transición de carrera hasta líderes técnicos y arquitectos— a partir de documentaciones y materiales técnicos densos y en constante evolución. `[EXP] (p.1)`

**Usuario directo del producto:** quien produce el material didáctico (especialista técnico, diseñador instruccional, formador). **El estudiante final es beneficiario, no operador** — ver §2.3. `[INF]`

### 1.3 Qué problema resuelve

Dos problemas, ambos declarados:

1. **Costo y latencia de producción.** La creación y adaptación manual de materiales didácticos a partir de documentaciones complejas "consume semanas de trabajo de especialistas y diseñadores instruccionales". `[EXP] (p.1)`
2. **Inaccesibilidad por audiencia.** Las documentaciones técnicas son "ricas, pero a menudo inaccesibles para quienes no dominan la jerga técnica avanzada"; un mismo manual "necesita enseñarse de maneras muy distintas" a un principiante y a un ejecutivo que decide inversión. `[EXP] (p.2)`

### 1.4 Qué valor proporciona

| Valor declarado | Fuente |
|---|---|
| Ingerir documentos técnicos densos **sin preprocesamiento manual** | `[EXP] (p.2)` |
| Personalizar lenguaje y didáctica **instantáneamente** para distintas audiencias | `[EXP] (p.2)` |
| Generar **múltiples formatos de estudio** con pocos clics | `[EXP] (p.2)` |
| **Confiabilidad:** el contenido no alucina y refleja fielmente el material original | `[EXP] (p.2)` |
| Reducir el tiempo de producción **de semanas a minutos** | `[EXP] (p.2)` |
| Salida **JSON estructurado** integrable con sistemas externos | `[EXP] (p.2)` |

> **Nota de posicionamiento `[INF]`:** el diferenciador competitivo declarado no es "generar contenido con IA" —eso es commodity— sino **generar contenido con fidelidad verificable a una fuente**. El campo `anclaje_fuente_score` `(p.5)` y el "mecanismo de verificación de fidelidad" `(p.3)` son, por tanto, funcionalidad de núcleo, no adorno. Esta lectura gobierna la priorización de §8.

---

## 2. Actors

### 2.1 Actores humanos

| ID | Actor | Objetivo | Interacción con el sistema | Fuente |
|---|---|---|---|---|
| **A1** | **Autor de Contenido Educativo** (especialista técnico / diseñador instruccional / formador) | Convertir un documento técnico denso en material didáctico listo para usar, en minutos y sin reescribirlo a mano | Carga el documento; selecciona perfil, formato y nicho; lanza la generación; revisa el paquete y su evaluación de calidad; descarga/consume el JSON | `[INF]` derivado de `(p.1-2)`: el documento describe el problema del especialista pero **nunca nombra al usuario operador** `[AMB]` |
| **A2** | **Estudiante / Destinatario Final** | Aprender el contenido técnico en el lenguaje y formato adecuados a su perfil | **En el MVP: ninguna interacción directa.** Es el beneficiario del paquete generado, no un usuario del sistema. Sólo interactúa si se implementa el diferencial opcional de Quiz en tiempo real `(p.6)` | `[EXP] (p.1-2)` como destinatario; `[INF]` la ausencia de interacción en MVP |
| **A3** | **Equipo de Desarrollo / Operador** | Poner el sistema en funcionamiento y mantenerlo dentro de la capa gratuita | Configura credenciales de LLM y de OCI, crea el bucket Always Free, despliega y opera | `[INF]` — necesario para que existan `[EXP] (p.4, p.6)` |
| **A4** | **Equipo Evaluador del Hackathon** | Verificar el cumplimiento de los requisitos mínimos | No opera el sistema en producción: **audita** el repositorio, el README con diagrama, y observa ≥3 ejemplos de ejecución y la adaptación a ≥2 perfiles y ≥2 formatos | `[EXP] (p.4, p.5-6)` |

> **Decisión de alcance `[INF]`:** A4 no es un actor del *software* pero **sí es un actor del producto** en este Hackathon: sus requisitos de verificabilidad (repositorio, README, diagrama, ejemplos reproducibles) generan requisitos funcionales reales (dominio D11, §3). Omitirlo es la forma más común de perder puntos de evaluación teniendo el sistema funcionando.

### 2.2 Actores sistema (externos)

| ID | Actor | Objetivo | Interacción | Fuente |
|---|---|---|---|---|
| **S1** | **Sistema Externo Consumidor** (LMS, plataforma educativa, pipeline de terceros) | Integrar el contenido generado en su propia plataforma | Consume el **JSON estructurado**, vía la salida del endpoint y/o leyendo el objeto persistido en el bucket | `[EXP] (p.2)`: "formato JSON estructurado para su integración con sistemas externos" |
| **S2** | **Proveedor de LLM** (Gemini, OpenAI, Claude, Grok, Ollama u otro) | — (servicio externo) | Recibe prompts estructurados; devuelve el contenido adaptado y la evaluación | `[EXP] (p.2, p.3, p.6)` — proveedor **a elección del equipo**, sin exclusividad |
| **S3** | **OCI Object Storage (Always Free)** | — (servicio externo obligatorio) | Recibe y almacena el documento original y el JSON del paquete generado | `[EXP] (p.2, p.4, p.6)` — **obligatorio** |

### 2.3 Roles internos del flujo (NO son actores)

El documento nombra cuatro roles de agente `(p.6)` —**Enrutador, Agente Investigador RAG, Agente Redactor Pedagógico, Agente Crítico/Revisor**— pero lo hace dentro de *"Recursos opcionales (Diferenciales)"*, bajo "Sistema Multi-Agente con LangGraph".

Simultáneamente, en *Resultados esperados* `(p.3)` exige una "cadena de orquestación **o** grafo de decisión para **planificar, redactar y revisar** el contenido generado" —es decir, **las tres responsabilidades son obligatorias; su materialización como agentes autónomos separados es opcional**. `[AMB]` resuelta así en esta especificación:

- **Obligatorio (MVP):** existen las tres responsabilidades lógicas —planificar, redactar, revisar— en el flujo.
- **Opcional (diferencial):** que estén implementadas como agentes autónomos enrutados en un grafo.

---

## 3. Functional Map

Clasificación por dominios. Se apartó del ejemplo propuesto en el brief en tres puntos, justificados abajo.

```
NuevaMente
│
├── D1  Document Ingestion            ── carga, extracción, normalización, identidad del documento
├── D2  Knowledge Indexing (RAG)      ── chunking, embeddings, vector store, recuperación
├── D3  Adaptation Parametrization    ── perfil, formato, nicho, nivel de detalle, validación de enums
├── D4  Content Generation & Orchestr.── planificar → redactar → revisar; prompts; LLM
├── D5  Pedagogical Evaluation        ── conceptos clave, prerrequisitos, tiempo, claridad pedagógica
├── D6  Source Fidelity Verification  ── anti-alucinación, anclaje_fuente_score, umbral
├── D7  Structured Output Contract    ── esquema de entrada y de salida, tipado estricto
├── D8  Persistence (OCI Object Stor.)── bucket Always Free, documento original + JSON generado
├── D9  User Interface & API          ── interfaz interactiva y/o API REST
├── D10 Validation & Error Handling   ── excepciones, mensajes amigables, contrato de error
├── D11 Evidence, Docs & Demo         ── repo, README, diagrama, ≥3 escenarios, ≥2 perfiles × ≥2 formatos
└── D12 Optional Differentials        ── OCI Compute, multi-agente, quiz en vivo, multimodal, export
```

### 3.1 Desviaciones respecto a la clasificación sugerida y por qué

| Cambio | Justificación |
|---|---|
| **Se separó D6 (Source Fidelity) de D5 (Pedagogical Evaluation)** | El documento los trata como cosas distintas y con dueños distintos: la evaluación pedagógica produce *metadatos de aprendizaje* `(p.2)`, mientras que la verificación de fidelidad es un *"mecanismo… para mitigar alucinaciones"* `(p.3)`. Fundirlos hace que la anti-alucinación —el diferenciador del producto— se diluya en una casilla de "calidad". En la salida ejemplo `(p.5)` conviven en el mismo objeto `evaluacion_calidad`, lo cual es una decisión de **contrato**, no de dominio. |
| **Se añadió D11 (Evidence, Docs & Demo)** | 3 de las 8 casillas del Checklist de Evaluación `(p.5-6)` no son funcionalidad de runtime: repositorio documentado con diagrama, ≥3 ejemplos de ejecución y demostración de ≥2 perfiles × ≥2 formatos. Si no se modelan como requisitos, no se planifican y no se cumplen. |
| **Se añadió D3 como dominio propio** | La parametrización (perfil / formato / nicho) no es "UI": es el **eje de valor del producto** y define el espacio de salidas válidas. Es la entrada semántica del sistema, independiente de si se expone por Streamlit o por REST. |
| **Se fundió "RAG" y "Content Adaptation" en D2 + D4** | El brief listaba "RAG" y "Content Adaptation" como grupos separados de "Content Generation". En el documento fuente la adaptación **es** el acto de generación parametrizada `(p.2, punto 2)`; no existe una etapa de adaptación posterior e independiente. Mantenerlas separadas inventaría una etapa que el documento no describe. |
---

## 4. Functional Requirements

Formato por requisito: **ID · Nombre · Descripción · Actor · Input · Processing · Output · Priority · Source · Dependencies**.
Prioridades: `MUST` / `SHOULD` / `COULD` / `OUT OF SCOPE`.

---

### D1 · Document Ingestion

#### FR-ING-01 · Carga de documento técnico
- **Descripción:** El sistema recibe un archivo con el material técnico a adaptar.
- **Actor:** A1
- **Input:** Archivo en formato PDF, Markdown o texto sin formato
- **Processing:** Recepción del archivo, verificación de formato soportado, registro de la carga
- **Output:** Documento aceptado y disponible para extracción, con identificador asignado
- **Priority:** `MUST`
- **Source:** `[EXP] (p.1)` "recibir materiales técnicos en los formatos soportados (archivos PDF, Markdown o texto sin formato)"; `[EXP] (p.3)` objetivo 1; Checklist casilla 1 `(p.5)`
- **Dependencies:** —

#### FR-ING-02 · Extracción de texto desde PDF
- **Descripción:** Extraer el contenido textual de un PDF sin intervención manual.
- **Actor:** Sistema
- **Input:** Archivo PDF aceptado (FR-ING-01)
- **Processing:** Extracción del texto página por página
- **Output:** Texto plano del documento, con referencia de página por fragmento
- **Priority:** `MUST`
- **Source:** `[EXP] (p.3)` "Ingestión y extracción de texto de documentos técnicos (ej.: biblioteca PyPDF…)"; la referencia de página por fragmento es `[INF]`, necesaria para FR-RAG-06 y FR-FID-01
- **Dependencies:** FR-ING-01

#### FR-ING-03 · Lectura de Markdown y texto plano
- **Descripción:** Leer e interpretar archivos `.md` y texto sin formato.
- **Actor:** Sistema
- **Input:** Archivo Markdown o texto plano
- **Processing:** Lectura del contenido; preservación de la jerarquía de encabezados cuando exista
- **Output:** Texto normalizado con su estructura de secciones
- **Priority:** `MUST`
- **Source:** `[EXP] (p.1, p.3)` "lectores Markdown"; la preservación de jerarquía es `[INF]` (mejora el chunking, no está pedida)
- **Dependencies:** FR-ING-01

#### FR-ING-04 · Ingesta de contenido técnico como texto embebido
- **Descripción:** Aceptar el material técnico directamente en el cuerpo de la solicitud, sin archivo, mediante `documento_titulo` + `documento_contenido`.
- **Actor:** A1, S1
- **Input:** `{ "documento_titulo": str, "documento_contenido": str }`
- **Processing:** Validación de presencia y no-vacío; tratamiento equivalente al de un documento extraído
- **Output:** Documento en memoria listo para indexación
- **Priority:** `MUST`
- **Source:** `[EXP] (p.4)` — el **Ejemplo de Solicitud oficial** del endpoint principal usa exactamente esta forma, no un archivo
- **Dependencies:** —
- **⚠ `[AMB]` A-01:** El documento exige ingestión de **archivos** PDF/MD/texto `(p.1, p.3, p.5)` pero el **único contrato de entrada documentado `(p.4)` recibe texto embebido**. No se aclara si son dos vías de entrada del mismo endpoint, dos endpoints, o si la UI hace la extracción y llama al endpoint con el texto ya extraído. Ver §11 Q-01.

#### FR-ING-05 · Normalización del texto extraído
- **Descripción:** Limpiar artefactos de extracción (cortes de línea espurios, encabezados/pies repetidos, numeración de página suelta) antes de segmentar.
- **Actor:** Sistema
- **Input:** Texto crudo extraído
- **Processing:** Normalización de espacios y saltos; eliminación de ruido repetitivo
- **Output:** Texto limpio apto para chunking
- **Priority:** `SHOULD`
- **Source:** `[INF]` — el documento promete ingerir "sin necesidad de preprocesamiento manual" `(p.2)`, lo que traslada al sistema una limpieza que hoy hace una persona. No se especifica su alcance.
- **Dependencies:** FR-ING-02, FR-ING-03

#### FR-ING-06 · Validación de entrada del documento
- **Descripción:** Rechazar con mensaje claro archivos de formato no soportado, vacíos, ilegibles o fuera del límite de tamaño.
- **Actor:** Sistema
- **Input:** Archivo o texto recibido
- **Processing:** Verificación de extensión/MIME, tamaño, extracción no vacía
- **Output:** Aceptación, o error tipificado y accionable
- **Priority:** `MUST`
- **Source:** `[INF]` derivado de `[EXP] (p.3)` "Validación de esquemas de entrada y salida con tipado estricto" y "Manejo de excepciones y mensajes de error amigables". **Límite de tamaño: TBD** — el documento no fija ninguno.
- **Dependencies:** FR-ING-01, FR-ERR-01

#### FR-ING-07 · Identidad del documento ingerido
- **Descripción:** Asignar un identificador único a cada documento ingerido para vincular documento original ↔ índice vectorial ↔ paquete generado ↔ objeto en OCI.
- **Actor:** Sistema
- **Input:** Documento aceptado
- **Processing:** Generación de identificador y registro de metadatos básicos (título, formato, fecha)
- **Output:** `document_id`
- **Priority:** `MUST`
- **Source:** `[INF]` — sin él no es posible cumplir FR-PER-01/02 (persistir *el par* documento+JSON) ni FR-PER-04 (nomenclatura del objeto), ambos `[EXP]`
- **Dependencies:** FR-ING-01

#### FR-ING-08 · OCR de documentos escaneados
- **Priority:** `OUT OF SCOPE`
- **Source:** No respaldado. El documento sólo contempla interpretación de imágenes bajo "Soporte Multimodal", explícitamente **opcional** `(p.6)`.

---

### D2 · Knowledge Indexing (RAG)

#### FR-RAG-01 · Segmentación en chunks
- **Descripción:** Dividir el texto del documento en fragmentos aptos para recuperación.
- **Actor:** Sistema
- **Input:** Texto normalizado + `document_id`
- **Processing:** Segmentación según estrategia y tamaño definidos
- **Output:** Colección de chunks con su metadato de origen
- **Priority:** `MUST`
- **Source:** `[EXP] (p.1, p.2, p.3)`; Checklist casilla 2 `(p.5)`. **Estrategia y tamaño de chunk: TBD** — no especificados.
- **Dependencies:** FR-ING-02/03/04/05

#### FR-RAG-02 · Generación de embeddings
- **Descripción:** Producir la representación vectorial de cada chunk.
- **Actor:** Sistema
- **Input:** Chunks
- **Processing:** Vectorización mediante un modelo de embeddings
- **Output:** Vectores asociados a cada chunk
- **Priority:** `MUST`
- **Source:** `[EXP] (p.1, p.2, p.3)`; Checklist casilla 2 `(p.5)`. **Modelo de embeddings: TBD.**
- **Dependencies:** FR-RAG-01

#### FR-RAG-03 · Almacenamiento en Vector Store
- **Descripción:** Persistir los vectores y sus metadatos en un almacén vectorial consultable.
- **Actor:** Sistema
- **Input:** Vectores + metadatos de chunk
- **Processing:** Indexación
- **Output:** Índice consultable para el documento
- **Priority:** `MUST`
- **Source:** `[EXP] (p.1, p.3)` "almacenamiento en Vector Store (ej.: Chroma, FAISS o similar)"; Checklist casilla 2 `(p.5)`
- **Dependencies:** FR-RAG-02

#### FR-RAG-04 · Búsqueda vectorial y recuperación de contexto
- **Descripción:** Recuperar los chunks más relevantes para fundamentar la generación.
- **Actor:** Sistema
- **Input:** Consulta derivada del documento y de los parámetros de adaptación
- **Processing:** Búsqueda por similitud sobre el índice
- **Output:** Conjunto de chunks recuperados, con su puntaje y su origen
- **Priority:** `MUST`
- **Source:** `[EXP] (p.1)` "búsqueda vectorial en Vector Store"; `(p.3)` "búsqueda de embeddings para anclar las respuestas"; Checklist casilla 2 `(p.5)`. **Número de chunks recuperados (k): TBD.**
- **Dependencies:** FR-RAG-03

#### FR-RAG-05 · Construcción de la consulta de recuperación
- **Descripción:** Derivar la(s) consulta(s) de recuperación a partir del documento y de los parámetros seleccionados (perfil / formato / nicho).
- **Actor:** Sistema
- **Input:** `document_id`, perfil, formato, nicho
- **Processing:** Formulación de consulta(s) de recuperación
- **Output:** Consulta(s) para FR-RAG-04
- **Priority:** `SHOULD`
- **Source:** `[INF]` — el documento exige recuperar contexto pero **nunca dice qué se consulta**. Es una decisión de diseño con impacto directo en la calidad de la salida. Ver §11 Q-05.
- **Dependencies:** FR-PAR-01/02/03, FR-RAG-04

#### FR-RAG-06 · Metadatos de trazabilidad por chunk
- **Descripción:** Conservar en cada chunk su `document_id`, posición y referencia de origen (página o sección).
- **Actor:** Sistema
- **Input:** Chunks
- **Processing:** Enriquecimiento con metadatos
- **Output:** Chunks trazables a su ubicación en el documento original
- **Priority:** `MUST`
- **Source:** `[INF]` — es la **precondición material** del "mecanismo de verificación de fidelidad al documento de origen" `[EXP] (p.3)`. Sin trazabilidad por chunk, `anclaje_fuente_score` sólo puede ser un número declarado por el LLM sobre sí mismo, no una verificación.
- **Dependencies:** FR-RAG-01

#### FR-RAG-07 · Ciclo de vida y aislamiento del índice
- **Descripción:** Definir si el índice vectorial es efímero por solicitud, persistente por documento, o acumulativo como base de conocimiento multi-documento.
- **Actor:** Sistema
- **Input:** `document_id`
- **Processing:** Creación / reutilización / expiración del índice
- **Output:** Índice con ciclo de vida definido
- **Priority:** `SHOULD`
- **Source:** `[INF]` · **⚠ `[AMB]` A-02** — El documento habla de "extraer e indexar" `(p.2)` sin decir si el índice sobrevive a la solicitud. Impacta directamente el costo de re-generar el mismo documento con otro perfil (caso central del Checklist casilla 4) y la persistencia Always Free. Ver §11 Q-06.
- **Dependencies:** FR-RAG-03

#### FR-RAG-08 · Re-ranking de resultados recuperados
- **Priority:** `COULD`
- **Source:** `[PROP]` — mejora conocida de precisión en RAG, **no pedida** por el documento. No entra al MVP.

---

### D3 · Adaptation Parametrization

#### FR-PAR-01 · Selección de Perfil del Destinatario
- **Descripción:** Permitir elegir el perfil al que se adaptará el contenido.
- **Actor:** A1, S1
- **Input:** Un valor del conjunto: `Principiante / Transición de Carrera`, `Desarrollador Junior / Semi Senior`, `Líder Técnico / Arquitecto`, `Gestor / Ejecutivo (No Técnico)`
- **Processing:** Validación contra el conjunto permitido; propagación al flujo de generación
- **Output:** Perfil aplicado, reflejado en `metadatos.perfil_aplicado`
- **Priority:** `MUST`
- **Source:** `[EXP] (p.1)`; reflejo en salida `[EXP] (p.5)`
- **Dependencies:** FR-PAR-05
- **⚠ `[AMB]` A-03:** El documento introduce los 4 valores con "ej.:" `(p.1)`, y el Ejemplo de Solicitud `(p.4)` usa `"Principiante"` —una **forma abreviada** que no coincide literalmente con `"Principiante / Transición de Carrera"`. No está definido si la lista es cerrada ni cuál es la forma canónica del valor. Ver §11 Q-02.

#### FR-PAR-02 · Selección de Formato Pedagógico de Salida
- **Descripción:** Permitir elegir el formato didáctico del paquete generado.
- **Actor:** A1, S1
- **Input:** Un valor del conjunto: `Guía Práctica Paso a Paso (Tutorial)`, `Flashcards de Memorización`, `Quiz Interactivo con Justificaciones`, `Resumen Ejecutivo (TL;DR)`, `Guion de Clase / Video`
- **Processing:** Validación; selección de la estructura de salida correspondiente
- **Output:** Formato aplicado, reflejado en `metadatos.formato_generado`
- **Priority:** `MUST`
- **Source:** `[EXP] (p.2)`; reflejo en salida `[EXP] (p.5)`
- **Dependencies:** FR-PAR-05, FR-OUT-05
- **⚠ `[AMB]` A-04:** mismo problema de forma canónica que A-03 (el ejemplo usa `"Flashcards"`).

#### FR-PAR-03 · Selección de Nicho / Contexto de Aplicación
- **Descripción:** Permitir elegir el sector que contextualiza ejemplos y analogías.
- **Actor:** A1, S1
- **Input:** Un valor del conjunto: `Fintech`, `Salud`, `E-commerce`, `General`
- **Processing:** Validación; propagación al flujo de generación como contexto de ejemplificación
- **Output:** Nicho aplicado
- **Priority:** `MUST`
- **Source:** `[EXP] (p.2)`
- **Dependencies:** FR-PAR-05
- **⚠ `[AMB]` A-05:** El nicho **no aparece en el objeto `metadatos` de la respuesta ejemplo** `(p.5)`, a diferencia del perfil y el formato. No está claro si debe reflejarse. Ver §11 Q-03.

#### FR-PAR-04 · Parámetro `nivel_detalle`
- **Descripción:** Modular la profundidad del contenido generado independientemente del perfil.
- **Actor:** A1, S1
- **Input:** Valor de tipo texto (ejemplo documentado: `"Didactico"`)
- **Processing:** Propagación al flujo de generación
- **Output:** Profundidad aplicada
- **Priority:** `SHOULD`
- **Source:** `[EXP] (p.4)` **sólo en el Ejemplo de Solicitud** · **⚠ `[AMB]` A-06** — Aparece en el contrato de entrada oficial pero **no está listado entre los criterios de parametrización** `(p.1-2)`, no tiene valores enumerados, no se define su relación con el perfil (¿son redundantes? ¿ortogonales?) y **no se refleja en la salida** `(p.5)`. Es el parámetro peor definido del documento. Ver §11 Q-04.
- **Dependencies:** FR-PAR-05

#### FR-PAR-05 · Validación de parámetros contra conjuntos permitidos
- **Descripción:** Rechazar valores fuera del conjunto permitido antes de consumir cuota de LLM.
- **Actor:** Sistema
- **Input:** Parámetros de la solicitud
- **Processing:** Validación tipada y de dominio
- **Output:** Parámetros validados, o error tipificado
- **Priority:** `MUST`
- **Source:** `[INF]` derivado de `[EXP] (p.3)` "Validación de esquemas de entrada… con tipado estricto" y `(p.6)` "parsers tipados… para asegurar el formato JSON correcto"
- **Dependencies:** FR-ERR-03

#### FR-PAR-06 · Obligatoriedad y valores por defecto de los parámetros
- **Descripción:** Definir qué parámetros son obligatorios y qué ocurre si falta alguno.
- **Actor:** Sistema
- **Priority:** `SHOULD`
- **Source:** `[INF]` · **⚠ `[AMB]` A-07** — El Ejemplo de Solicitud `(p.4)` envía los 6 campos, pero nada indica si son obligatorios. Ver §11 Q-07.
- **Dependencies:** FR-PAR-05

---

### D4 · Content Generation & Orchestration

#### FR-GEN-01 · Orquestación del flujo planificar → redactar → revisar
- **Descripción:** Ejecutar el flujo de generación como una cadena o grafo con etapas diferenciadas de planificación, redacción y revisión.
- **Actor:** Sistema
- **Input:** Chunks recuperados + parámetros validados
- **Processing:** Planificación de la estructura del paquete; redacción; revisión del resultado
- **Output:** Contenido adaptado, revisado, listo para estructurar
- **Priority:** `MUST`
- **Source:** `[EXP] (p.3)` "Cadena de orquestación (LangChain) o Grafo de Decisión (LangGraph) para planificar, redactar y revisar el contenido generado"; `(p.2)` "Orquestar un flujo de agentes o cadenas de prompts"; Checklist casilla 3 `(p.5)`
- **Dependencies:** FR-RAG-04, FR-PAR-05

#### FR-GEN-02 · Prompts estructurados con few-shot y role prompting
- **Descripción:** Construir los prompts del flujo aplicando role prompting y ejemplos few-shot.
- **Actor:** Sistema
- **Input:** Contexto recuperado, parámetros, plantillas de prompt
- **Processing:** Composición del prompt por etapa y por formato de salida
- **Output:** Prompt enviado al LLM
- **Priority:** `MUST`
- **Source:** `[EXP] (p.3)` "Creación y optimización de prompts estructurados con técnicas de few-shot y role prompting"
- **Dependencies:** FR-GEN-01

#### FR-GEN-03 · Adaptación de lenguaje, profundidad y tono al perfil
- **Descripción:** Reescribir el contenido técnico al registro propio del perfil seleccionado.
- **Actor:** Sistema
- **Input:** Contexto recuperado + perfil
- **Processing:** Reescritura con el nivel de profundidad y tono adecuados
- **Output:** Texto adaptado al perfil
- **Priority:** `MUST`
- **Source:** `[EXP] (p.2)` "reescribir… en el nivel de profundidad y tono adecuados"; `(p.2)` "Personalizar el lenguaje y la didáctica"; Checklist casilla 4 `(p.5)`
- **Dependencies:** FR-GEN-01, FR-PAR-01

#### FR-GEN-04 · Ejemplificación contextualizada al nicho
- **Descripción:** Generar analogías y ejemplos anclados en el sector seleccionado.
- **Actor:** Sistema
- **Input:** Contenido adaptado + nicho
- **Processing:** Ejemplificación sectorial
- **Output:** Contenido con ejemplos del nicho
- **Priority:** `MUST`
- **Source:** `[EXP] (p.2)` "reescribir, **ejemplificar** y estructurar"; el nicho es criterio de parametrización `[EXP] (p.2)`
- **Dependencies:** FR-GEN-03, FR-PAR-03

#### FR-GEN-05 · Estructuración según el formato pedagógico
- **Descripción:** Organizar el contenido en la estructura propia del formato elegido.
- **Actor:** Sistema
- **Input:** Contenido adaptado + formato
- **Processing:** Estructuración en la forma del formato (pasos, tarjetas, preguntas, resumen, guion)
- **Output:** `contenido_adaptado` estructurado
- **Priority:** `MUST`
- **Source:** `[EXP] (p.2, p.3)`; Checklist casilla 4 `(p.5)`
- **Dependencies:** FR-GEN-03, FR-OUT-05

#### FR-GEN-06 · Título e introducción contextualizada
- **Descripción:** Generar un título didáctico y una introducción que contextualice al destinatario.
- **Actor:** Sistema
- **Input:** Contenido adaptado, perfil, nicho
- **Processing:** Generación de `titulo` e `introduccion_contextualizada`
- **Output:** Ambos campos poblados
- **Priority:** `MUST`
- **Source:** `[EXP] (p.5)` — ambos campos son parte del contrato de salida documentado
- **Dependencies:** FR-GEN-03

#### FR-GEN-07 · Generación de ítems según la estructura de cada formato
- **Descripción:** Producir el arreglo `items[]` con la forma que corresponde al formato seleccionado.
- **Actor:** Sistema
- **Input:** Contenido estructurado + formato
- **Processing:** Generación de los ítems tipados del formato
- **Output:** `contenido_adaptado.items[]`
- **Priority:** `MUST`
- **Source:** `[EXP] (p.5)` **únicamente para Flashcards** (`frente`, `dorso`, `pista_didactica`) · **⚠ `[AMB]` A-08 — la ambigüedad de mayor impacto del documento:** se exigen **5 formatos pedagógicos** `(p.2)` pero se documenta la estructura de **uno solo**. Las estructuras de Tutorial, Quiz con justificaciones, TL;DR y Guion de Clase **no existen en la fuente** y deben ser definidas por el equipo. Ver §11 Q-08.
- **Dependencies:** FR-GEN-05, FR-OUT-05

#### FR-GEN-08 · Recuperación ante salida no parseable del LLM
- **Descripción:** Reintentar o reparar cuando la respuesta del LLM no cumple el esquema tipado.
- **Actor:** Sistema
- **Input:** Respuesta cruda del LLM
- **Processing:** Validación; reintento acotado o reparación
- **Output:** Salida conforme al esquema, o error tipificado
- **Priority:** `SHOULD`
- **Source:** `[INF]` — consecuencia operativa directa de exigir "tipado estricto" `[EXP] (p.3)` sobre una fuente no determinista. **Número de reintentos: TBD.**
- **Dependencies:** FR-OUT-02, FR-ERR-02

#### FR-GEN-09 · Sistema multi-agente con enrutador
- **Descripción:** Materializar el flujo como agentes autónomos: Enrutador, Agente Investigador RAG, Agente Redactor Pedagógico, Agente Crítico/Revisor.
- **Priority:** `COULD`
- **Source:** `[EXP] (p.6)` — listado explícitamente bajo "Recursos opcionales (Diferenciales)". **No es MVP.** Las tres responsabilidades lógicas sí lo son (FR-GEN-01).
- **Dependencies:** FR-GEN-01

#### FR-GEN-10 · Reproducibilidad de la generación
- **Descripción:** Fijar parámetros de muestreo para que los escenarios de demostración sean repetibles.
- **Priority:** `COULD`
- **Source:** `[PROP]` — no pedido. Nota: tiene valor desproporcionado frente a su costo, porque el Checklist exige **demostrar** ≥3 escenarios `(p.5-6)` ante evaluadores, y una demo no reproducible es un riesgo de presentación (ver R-09).

---

### D5 · Pedagogical Evaluation

#### FR-EVA-01 · Extracción de conceptos clave
- **Descripción:** Identificar los conceptos centrales del contenido generado.
- **Actor:** Sistema
- **Input:** Contenido adaptado + contexto fuente
- **Processing:** Extracción de conceptos
- **Output:** `metadatos.conceptos_clave: [str]`
- **Priority:** `MUST`
- **Source:** `[EXP] (p.2)` "generar metadatos de aprendizaje (conceptos clave…)"; `(p.3)` objetivo 4 "términos clave"; `(p.5)` campo en la salida
- **Dependencies:** FR-GEN-05

#### FR-EVA-02 · Estimación de tiempo de estudio
- **Descripción:** Estimar en minutos el tiempo de estudio del paquete.
- **Actor:** Sistema
- **Input:** Paquete generado
- **Processing:** Estimación
- **Output:** `metadatos.tiempo_estimado_estudio_minutos: int`
- **Priority:** `MUST`
- **Source:** `[EXP] (p.2)` "tiempo estimado de estudio"; `(p.5)` campo en la salida. **Método de estimación: TBD.**
- **Dependencies:** FR-GEN-05

#### FR-EVA-03 · Identificación de prerrequisitos
- **Descripción:** Determinar los conocimientos previos necesarios para el paquete.
- **Actor:** Sistema
- **Input:** Contenido adaptado + perfil
- **Processing:** Identificación de prerrequisitos
- **Output:** Campo de prerrequisitos en metadatos
- **Priority:** `SHOULD`
- **Source:** `[EXP] (p.2)` "metadatos de aprendizaje (conceptos clave, **prerrequisitos**, tiempo estimado de estudio)" · **⚠ `[AMB]` A-09** — Exigido en el cuerpo del documento pero **ausente del contrato de salida ejemplo** `(p.5)`. Contradicción directa entre dos secciones. Ver §11 Q-09.
- **Dependencies:** FR-GEN-05

#### FR-EVA-04 · Evaluación de coherencia y claridad pedagógica
- **Descripción:** Evaluar la adecuación didáctica del paquete al perfil declarado.
- **Actor:** Sistema
- **Input:** Paquete generado + perfil
- **Processing:** Evaluación de coherencia didáctica
- **Output:** `evaluacion_calidad.claridad_pedagogica`
- **Priority:** `MUST`
- **Source:** `[EXP] (p.2)` "Evaluar la coherencia didáctica"; `(p.3)` objetivo 4 "evaluación pedagógica"; `(p.5)` campo con valor `"Alta"`. **Escala de valores: TBD** — sólo se conoce un valor de ejemplo.
- **Dependencies:** FR-GEN-05

#### FR-EVA-05 · Observaciones cualitativas de la evaluación
- **Descripción:** Justificar en texto la evaluación emitida.
- **Actor:** Sistema
- **Input:** Resultado de FR-EVA-04 y FR-FID-02
- **Processing:** Redacción de la observación
- **Output:** `evaluacion_calidad.observaciones: str`
- **Priority:** `MUST`
- **Source:** `[EXP] (p.5)` — campo del contrato de salida
- **Dependencies:** FR-EVA-04

#### FR-EVA-06 · Reflejo de parámetros aplicados en metadatos
- **Descripción:** Devolver en la respuesta el perfil y el formato efectivamente aplicados.
- **Actor:** Sistema
- **Input:** Parámetros validados
- **Processing:** Copia a la sección de metadatos
- **Output:** `metadatos.perfil_aplicado`, `metadatos.formato_generado`
- **Priority:** `MUST`
- **Source:** `[EXP] (p.5)`
- **Dependencies:** FR-PAR-01, FR-PAR-02

---

### D6 · Source Fidelity Verification

#### FR-FID-01 · Mecanismo de verificación de fidelidad a la fuente
- **Descripción:** Verificar que el contenido generado está sustentado en el documento original, para mitigar alucinaciones.
- **Actor:** Sistema
- **Input:** Contenido generado + chunks recuperados con sus metadatos de origen
- **Processing:** Contraste del contenido generado contra el contexto fuente
- **Output:** Veredicto de fidelidad, insumo de FR-FID-02
- **Priority:** `MUST`
- **Source:** `[EXP] (p.3)` "Mecanismo de verificación de fidelidad al documento de origen para mitigar alucinaciones"; `(p.2)` "asegurando que los contenidos generados no alucinen y reflejen fielmente el material original". **Método: TBD** — el documento exige el mecanismo pero no lo define.
- **Dependencies:** FR-RAG-06, FR-GEN-01

#### FR-FID-02 · Puntaje de anclaje a la fuente
- **Descripción:** Emitir un puntaje cuantitativo de anclaje en el contrato de salida.
- **Actor:** Sistema
- **Input:** Veredicto de FR-FID-01
- **Processing:** Cálculo del puntaje
- **Output:** `evaluacion_calidad.anclaje_fuente_score` (valor de ejemplo: `0.98`)
- **Priority:** `MUST`
- **Source:** `[EXP] (p.5)` · **⚠ `[AMB]` A-10** — Se documenta el campo y un valor, pero **no la escala, ni el método de cálculo, ni su significado**. Un número producido por el propio LLM que se autoevalúa no constituye verificación (ver R-02). Ver §11 Q-10.
- **Dependencies:** FR-FID-01

#### FR-FID-03 · Umbral de aceptación y acción correctiva
- **Descripción:** Definir el puntaje mínimo aceptable y qué hace el sistema por debajo de él (regenerar, marcar, o rechazar).
- **Actor:** Sistema
- **Input:** `anclaje_fuente_score`
- **Processing:** Comparación contra umbral; acción correctiva
- **Output:** Paquete aceptado, regenerado o marcado
- **Priority:** `SHOULD`
- **Source:** `[INF]` — un puntaje sin umbral no "mitiga" nada; es un reporte. La etapa de "revisar" `[EXP] (p.3)` implica que el flujo puede actuar sobre lo revisado. **Umbral: TBD.** Ver §11 Q-11.
- **Dependencies:** FR-FID-02

#### FR-FID-04 · Citación de fragmentos fuente por ítem generado
- **Descripción:** Asociar cada ítem del paquete a los fragmentos del documento que lo sustentan.
- **Priority:** `COULD`
- **Source:** `[PROP]` — no pedido por el documento. Nota: es la forma más directa de hacer **auditable** el `anclaje_fuente_score` y de demostrar la anti-alucinación ante los evaluadores; su costo es bajo si FR-RAG-06 ya existe.
- **Dependencies:** FR-RAG-06, FR-FID-01

---

### D7 · Structured Output Contract

#### FR-OUT-01 · Contrato de salida JSON
- **Descripción:** Devolver el paquete educativo en un JSON con las cinco secciones documentadas.
- **Actor:** Sistema → A1, S1
- **Input:** Resultados de D4, D5, D6, D8
- **Processing:** Composición del objeto de respuesta
- **Output:** JSON con `status`, `metadatos`, `contenido_adaptado`, `evaluacion_calidad`, `almacenamiento_oci`
- **Priority:** `MUST`
- **Source:** `[EXP] (p.4-5)` Ejemplo de Respuesta; `(p.2, p.3)`; Checklist casilla 5 `(p.5)`
- **Dependencies:** FR-EVA-*, FR-FID-02, FR-PER-03

#### FR-OUT-02 · Validación de la salida contra esquema tipado estricto
- **Descripción:** Validar la respuesta antes de devolverla y antes de persistirla.
- **Actor:** Sistema
- **Input:** Objeto de respuesta candidato
- **Processing:** Validación tipada
- **Output:** Respuesta válida, o error tipificado
- **Priority:** `MUST`
- **Source:** `[EXP] (p.3)` "Validación de esquemas de entrada y salida con tipado estricto"; `(p.6)` "Utilice parsers tipados… para asegurar el formato JSON correcto"
- **Dependencies:** FR-OUT-01

#### FR-OUT-03 · Contrato de entrada JSON
- **Descripción:** Aceptar la solicitud con los campos documentados.
- **Actor:** A1, S1
- **Input:** `documento_titulo`, `documento_contenido`, `perfil_destinatario`, `formato_salida`, `nicho_sector`, `nivel_detalle`
- **Processing:** Validación tipada y de dominio
- **Output:** Solicitud validada
- **Priority:** `MUST`
- **Source:** `[EXP] (p.4)` Ejemplo de Solicitud
- **Dependencies:** FR-PAR-05, FR-ING-04

#### FR-OUT-04 · Campo `status` de resultado
- **Descripción:** Señalar el resultado de la operación en el contrato.
- **Actor:** Sistema
- **Input:** Resultado del flujo
- **Processing:** Asignación del estado
- **Output:** `status` (valor documentado de éxito: `"exito"`)
- **Priority:** `MUST`
- **Source:** `[EXP] (p.4)` para el caso de éxito; `[INF]` para los valores de error — **no documentados**. Ver §11 Q-12.
- **Dependencies:** FR-OUT-01, FR-ERR-03

#### FR-OUT-05 · Variantes tipadas de `contenido_adaptado` por formato
- **Descripción:** Definir un esquema tipado distinto de `items[]` para cada uno de los 5 formatos pedagógicos.
- **Actor:** Sistema
- **Input:** Formato seleccionado
- **Processing:** Selección del esquema aplicable; validación contra él
- **Output:** `items[]` conforme al esquema del formato
- **Priority:** `MUST`
- **Source:** `[INF]` — es la única forma de que FR-GEN-07 y FR-OUT-02 (`[EXP]` ambos) sean simultáneamente satisfacibles con 5 formatos. Depende de resolver A-08.
- **Dependencies:** FR-GEN-07, FR-OUT-02

#### FR-OUT-06 · Versionado del esquema de salida
- **Priority:** `COULD`
- **Source:** `[PROP]` — buena práctica para consumo por sistemas externos (S1), no pedida.

---

### D8 · Persistence — OCI Object Storage

#### FR-PER-01 · Persistir el documento técnico original
- **Descripción:** Almacenar en el bucket Always Free el documento original enviado.
- **Actor:** Sistema → S3
- **Input:** Documento ingerido + `document_id`
- **Processing:** Carga del objeto al bucket
- **Output:** Objeto persistido con su identificador
- **Priority:** `MUST`
- **Source:** `[EXP] (p.4)` "persistir los documentos técnicos originales enviados"; `(p.2)`; Checklist casilla 6 `(p.6)`
- **Dependencies:** FR-ING-07

#### FR-PER-02 · Persistir el JSON del paquete educativo generado
- **Descripción:** Almacenar en el mismo bucket el JSON de contenido educativo adaptado.
- **Actor:** Sistema → S3
- **Input:** JSON validado (FR-OUT-02)
- **Processing:** Carga del objeto al bucket
- **Output:** Objeto JSON persistido
- **Priority:** `MUST`
- **Source:** `[EXP] (p.4)` "y los archivos JSON de contenido educativo adaptado generados por el sistema"; Checklist casilla 6 `(p.6)`
- **Dependencies:** FR-OUT-02

#### FR-PER-03 · Reportar el resultado de la persistencia en la respuesta
- **Descripción:** Incluir en la respuesta los datos del almacenamiento.
- **Actor:** Sistema
- **Input:** Resultado de FR-PER-01/02
- **Processing:** Composición de la sección
- **Output:** `almacenamiento_oci: { bucket, objeto_id, status_upload }`
- **Priority:** `MUST`
- **Source:** `[EXP] (p.5)`
- **Dependencies:** FR-PER-02, FR-OUT-01
- **⚠ `[AMB]` A-11:** La sección reporta **un solo** `objeto_id`, pero se persisten **dos** artefactos (documento original + JSON). No está definido cómo se reporta el documento original. Ver §11 Q-13.

#### FR-PER-04 · Convención de nomenclatura de objetos
- **Descripción:** Nombrar los objetos de forma legible y trazable al documento y a los parámetros.
- **Actor:** Sistema
- **Input:** `document_id`, perfil, formato
- **Processing:** Composición del nombre
- **Output:** `objeto_id` (patrón evidenciado: `contenido-vcn-principiante-flashcards-001.json`)
- **Priority:** `MUST`
- **Source:** `[EXP] (p.5)` por evidencia del ejemplo; la **regla exacta es `[INF]`** — se infiere `contenido-<slug_documento>-<perfil>-<formato>-<secuencial>.json`. **Confirmar.**
- **Dependencies:** FR-PER-02

#### FR-PER-05 · Restricción de capa Always Free
- **Descripción:** Usar exclusivamente servicios y configuraciones de la capa Always Free de OCI.
- **Actor:** A3
- **Priority:** `MUST` — **restricción transversal, no funcionalidad.** No tiene `Input` / `Processing` / `Output` porque no es una operación: condiciona toda decisión de infraestructura del proyecto
- **Source:** `[EXP] (p.4)` "Aviso Importante ONE"; `(p.7)` "Atención a los Costos… exclusivamente servicios de la capa Always Free"
- **Dependencies:** —

#### FR-PER-06 · Comportamiento ante fallo de persistencia
- **Descripción:** Definir si un fallo de carga a OCI invalida la operación completa o si se devuelve el contenido generado marcando el fallo.
- **Actor:** Sistema
- **Input:** Error de carga
- **Processing:** Política de fallo definida
- **Output:** `status` y `almacenamiento_oci.status_upload` coherentes con la política
- **Priority:** `MUST` (la decisión), `SHOULD` (la ruta degradada)
- **Source:** `[INF]` · **⚠ `[AMB]` A-12** — El campo `status_upload` `(p.5)` implica que la carga **puede no estar completada**, pero la política no está definida. Es una decisión de producto con impacto en la demo: si OCI está en la ruta crítica, un fallo de red durante la presentación cuesta la demostración completa. Ver §11 Q-14.
- **Dependencies:** FR-PER-01, FR-PER-02, FR-ERR-04

#### FR-PER-07 · Recuperación y listado de paquetes ya generados
- **Priority:** `COULD`
- **Source:** `[PROP]` — el documento exige *escritura* en Object Storage, nunca *lectura*. No entra al MVP.

#### FR-PER-08 · Persistencia del índice vectorial en OCI
- **Priority:** `OUT OF SCOPE`
- **Source:** El documento delimita el uso obligatorio de Object Storage a "los documentos técnicos originales enviados y los archivos JSON… generados" `[EXP] (p.4)`. El índice no está incluido.

---

### D9 · User Interface & API

#### FR-UXA-01 · Interfaz de carga y parametrización
- **Descripción:** Interfaz interactiva para cargar el documento y seleccionar perfil, formato y nicho.
- **Actor:** A1
- **Input:** Archivo o texto + selección de parámetros
- **Processing:** Envío al flujo de generación
- **Output:** Solicitud enviada; resultado renderizado
- **Priority:** `MUST`
- **Source:** `[EXP] (p.3)` "Endpoint o interfaz para cargar el documento técnico y seleccionar los parámetros (perfil, formato, nicho)"; `(p.2)`; Checklist casilla 5 `(p.5)`
- **Dependencies:** FR-ING-01, FR-PAR-01/02/03

#### FR-UXA-02 · Visualización del paquete generado
- **Descripción:** Mostrar el paquete educativo de forma legible, incluyendo metadatos y evaluación de calidad.
- **Actor:** A1
- **Input:** JSON de respuesta
- **Processing:** Renderizado según formato
- **Output:** Vista legible del paquete
- **Priority:** `MUST`
- **Source:** `[EXP] (p.6)` "visualización de los resultados generados"
- **Dependencies:** FR-OUT-01

#### FR-UXA-03 · Endpoint principal de Adaptación de Contenido Educativo
- **Descripción:** Exponer la acción principal que recibe material + parámetros y retorna el paquete completo.
- **Actor:** A1, S1
- **Input:** Contrato de entrada (FR-OUT-03)
- **Processing:** Orquestación completa del flujo
- **Output:** Contrato de salida (FR-OUT-01)
- **Priority:** `MUST`
- **Source:** `[EXP] (p.4)` "Funcionalidades obligatorias (MVP) — Endpoint / Acción Principal: Adaptación de Contenido Educativo"
- **Dependencies:** todo D1–D8
- **⚠ `[AMB]` A-13:** El Checklist `(p.5)` pide "interfaz interactiva **o** API REST operativa" (disyunción), pero la sección de Funcionalidades obligatorias `(p.4)` exige el endpoint/acción principal y los Resultados esperados `(p.3)` piden "Endpoint **o** interfaz". Queda abierto si basta una sola superficie. Ver §11 Q-15.

#### FR-UXA-04 · Acceso al JSON crudo desde la interfaz
- **Descripción:** Permitir ver y/o descargar el JSON estructurado tal cual se produce.
- **Actor:** A1, A4
- **Priority:** `SHOULD`
- **Source:** `[INF]` — es la evidencia más directa del Checklist casilla 5 ("salida de datos estructurada en JSON") ante un evaluador que sólo ve la UI.
- **Dependencies:** FR-OUT-01

#### FR-UXA-05 · Indicación de progreso durante la generación
- **Descripción:** Informar el avance mientras el flujo se ejecuta.
- **Actor:** A1
- **Priority:** `SHOULD`
- **Source:** `[INF]` — un flujo RAG + múltiples llamadas a LLM tiene latencia perceptible; sin indicación, la interfaz parece colgada.
- **Dependencies:** FR-UXA-01

#### FR-UXA-06 · Comparación de escenarios sobre el mismo documento
- **Descripción:** Generar y mostrar lado a lado la adaptación del mismo documento para distintos perfiles y/o formatos.
- **Actor:** A1, A4
- **Priority:** `SHOULD`
- **Source:** `[INF]` — el Checklist exige demostrar ≥2 perfiles y ≥2 formatos `(p.5)` y ≥3 escenarios sobre un mismo documento `(p.4)`. Esta funcionalidad **convierte el requisito de evaluación en una capacidad visible del producto**, en lugar de en tres ejecuciones sueltas. Alto retorno para el esfuerzo.
- **Dependencies:** FR-UXA-02

#### FR-UXA-07 · Quiz interactivo con retroalimentación en tiempo real
- **Priority:** `COULD`
- **Source:** `[EXP] (p.6)` — "Recursos opcionales (Diferenciales)". **Único caso en que A2 (Estudiante) se vuelve usuario del sistema.**

#### FR-UXA-08 · Autenticación y gestión de usuarios
- **Priority:** `OUT OF SCOPE`
- **Source:** No mencionada en ninguna parte del documento.

#### FR-UXA-09 · Historial de generaciones por usuario
- **Priority:** `OUT OF SCOPE`
- **Source:** No respaldado. Requeriría FR-UXA-08 y FR-PER-07.

---

### D10 · Validation & Error Handling

#### FR-ERR-01 · Mensajes de error amigables
- **Descripción:** Comunicar los fallos en lenguaje comprensible y accionable para el usuario.
- **Actor:** Sistema → A1
- **Input:** Excepción capturada
- **Processing:** Traducción a mensaje de usuario
- **Output:** Mensaje claro, sin trazas técnicas expuestas
- **Priority:** `MUST`
- **Source:** `[EXP] (p.3)` "Manejo de excepciones y mensajes de error amigables"
- **Dependencies:** FR-ERR-02

#### FR-ERR-02 · Manejo de excepciones en toda la cadena
- **Descripción:** Capturar y tipificar fallos en ingesta, embeddings, vector store, LLM y OCI.
- **Actor:** Sistema
- **Input:** Excepciones de cada etapa
- **Processing:** Captura, clasificación, registro
- **Output:** Error tipificado propagado al contrato
- **Priority:** `MUST`
- **Source:** `[EXP] (p.3)`
- **Dependencies:** —

#### FR-ERR-03 · Contrato de error consistente
- **Descripción:** Devolver los errores con una estructura JSON estable y tipada.
- **Actor:** Sistema → S1
- **Input:** Error tipificado
- **Processing:** Composición de la respuesta de error
- **Output:** JSON de error con `status` y detalle
- **Priority:** `MUST`
- **Source:** `[INF]` derivado de FR-OUT-02 y FR-OUT-04 (`[EXP]`). La **forma del error no está documentada** — sólo existe el ejemplo de éxito `(p.4-5)`. Ver §11 Q-12.
- **Dependencies:** FR-OUT-04, FR-ERR-02

#### FR-ERR-04 · Degradación controlada
- **Descripción:** Permitir que el fallo de una etapa no crítica no invalide todo el resultado, señalándolo en la respuesta.
- **Actor:** Sistema
- **Priority:** `SHOULD`
- **Source:** `[INF]` — depende de la política de FR-PER-06 (A-12).
- **Dependencies:** FR-PER-06

#### FR-ERR-05 · Tiempos límite y política de reintentos
- **Descripción:** Acotar la espera y los reintentos ante servicios externos (LLM, embeddings, OCI).
- **Actor:** Sistema
- **Priority:** `SHOULD`
- **Source:** `[INF]` — **valores: TBD**, el documento no fija ninguno.
- **Dependencies:** FR-ERR-02

---

### D11 · Evidence, Docs & Demo

> Dominio no-runtime. Son entregables evaluados: **3 de las 8 casillas del Checklist viven aquí.**
>
> Los campos `Input` / `Processing` / `Output` se omiten deliberadamente en este dominio: no describen operaciones del sistema en ejecución sino artefactos entregables. Rellenarlos sería inventar semántica que el documento no respalda.

#### FR-DOC-01 · Repositorio Git estructurado
- **Descripción:** Repositorio con estructura clara y commits claros y colaborativos.
- **Actor:** A3 → A4
- **Priority:** `MUST`
- **Source:** `[EXP] (p.4)`; Checklist casilla 8 `(p.6)`

#### FR-DOC-02 · README con arquitectura, diagrama y guía de instalación
- **Descripción:** README.md detallado con la arquitectura de la solución, **diagrama del flujo RAG/Agentes** y guía de instalación.
- **Actor:** A3 → A4
- **Priority:** `MUST`
- **Source:** `[EXP] (p.4)`; Checklist casilla 8 `(p.6)` "Documentación completa… con diagrama de arquitectura"

#### FR-DOC-03 · Tres escenarios de adaptación sobre un mismo documento
- **Descripción:** Demostración práctica de **al menos tres escenarios distintos de adaptación para un mismo documento técnico**.
- **Actor:** A3 → A4
- **Priority:** `MUST`
- **Source:** `[EXP] (p.4)`
- **Dependencies:** FR-UXA-06

#### FR-DOC-04 · Tres ejemplos de ejecución documentados
- **Descripción:** Presentación de un mínimo de 3 ejemplos de ejecución con documentaciones reales o simuladas.
- **Actor:** A3 → A4
- **Priority:** `MUST`
- **Source:** `[EXP] (p.6)` Checklist casilla 7
- **⚠ `[AMB]` A-14:** FR-DOC-03 `(p.4)` exige 3 escenarios **sobre un mismo documento**; FR-DOC-04 `(p.6)` exige 3 ejemplos de ejecución **con documentaciones reales o simuladas** (plural, sin restricción de unicidad). Pueden ser el mismo requisito enunciado dos veces, o dos requisitos distintos. **Interpretación conservadora adoptada:** satisfacer ambos — 3 escenarios sobre un documento común **y** al menos un segundo documento distinto entre los ejemplos. Ver §11 Q-16.

#### FR-DOC-05 · Notebook o módulos que evidencien la pipeline
- **Descripción:** Entregar el notebook o los módulos que contengan ingestión, pipeline RAG, prompts, orquestación y verificación de fidelidad.
- **Actor:** A3 → A4
- **Priority:** `MUST`
- **Source:** `[EXP] (p.3)` "Notebook o módulos que contengan…"

#### FR-DOC-06 · Evidencia de cobertura de ≥2 perfiles y ≥2 formatos
- **Descripción:** Demostrar que el mismo contenido se adapta a al menos 2 perfiles diferentes y 2 formatos distintos.
- **Actor:** A3 → A4
- **Priority:** `MUST`
- **Source:** `[EXP] (p.5)` Checklist casilla 4
- **Dependencies:** FR-GEN-03, FR-GEN-05

---

### D12 · Optional Differentials

| ID | Nombre | Priority | Source |
|---|---|---|---|
| FR-OPT-01 | Despliegue completo en la nube (OCI Compute Always Free, VM Linux) | `COULD` | `[EXP] (p.4, p.6)` — "Recurso Opcional / Diferencial" |
| FR-OPT-02 | Sistema Multi-Agente con LangGraph (= FR-GEN-09) | `COULD` | `[EXP] (p.6)` |
| FR-OPT-03 | Quiz con evaluación en tiempo real (= FR-UXA-07) | `COULD` | `[EXP] (p.6)` |
| FR-OPT-04 | Soporte multimodal: interpretación de diagramas técnicos del documento | `COULD` | `[EXP] (p.6)` |
| FR-OPT-05 | Exportación multiformato: Markdown, PDF didáctico, CSV compatible con Anki | `COULD` | `[EXP] (p.6)` |
---

## 5. User Stories (sólo requisitos MUST)

Cada historia agrupa uno o más FR `MUST`. La cobertura se audita en §9.

| ID | Historia | FR cubiertos |
|---|---|---|
| **US-01** | Como **Autor de Contenido**, quiero **cargar un documento técnico en PDF, Markdown o texto plano**, para **no tener que convertir ni preparar el material a mano antes de usarlo**. | FR-ING-01, 02, 03, 06 |
| **US-02** | Como **Sistema Externo Consumidor**, quiero **enviar el material técnico como texto dentro de la solicitud**, para **integrar la generación en mi propio flujo sin manejar archivos**. | FR-ING-04, FR-OUT-03 |
| **US-03** | Como **Autor de Contenido**, quiero que **el sistema indexe automáticamente el documento en fragmentos vectorizados**, para **que el contenido generado pueda apoyarse en el material real y no en el conocimiento general del modelo**. | FR-ING-07, FR-RAG-01, 02, 03 |
| **US-04** | Como **Autor de Contenido**, quiero que **la generación se construya sobre fragmentos recuperados del propio documento**, para **que lo que se enseñe provenga de mi fuente y sea rastreable hasta ella**. | FR-RAG-04, FR-RAG-06 |
| **US-05** | Como **Autor de Contenido**, quiero **elegir perfil del destinatario, formato pedagógico y nicho de aplicación**, para **obtener material dirigido a una audiencia concreta en lugar de un texto genérico**. | FR-PAR-01, 02, 03, 05 |
| **US-06** | Como **Autor de Contenido**, quiero que **el contenido se reescriba en el lenguaje, la profundidad y el tono del perfil elegido**, para **poder enseñar el mismo manual a un principiante y a un arquitecto sin reescribirlo dos veces**. | FR-GEN-01, 02, 03 |
| **US-07** | Como **Autor de Contenido**, quiero que **los ejemplos y analogías correspondan al nicho seleccionado**, para **que el material le resulte relevante y familiar a la audiencia de ese sector**. | FR-GEN-04 |
| **US-08** | Como **Autor de Contenido**, quiero **recibir el contenido ya estructurado en el formato pedagógico que elegí**, para **poder usarlo tal cual sin rearmarlo**. | FR-GEN-05, 06, 07, FR-OUT-05 |
| **US-09** | Como **Autor de Contenido**, quiero **recibir los conceptos clave y el tiempo estimado de estudio junto al contenido**, para **planificar la sesión formativa sin analizar el material yo mismo**. | FR-EVA-01, 02, 06 |
| **US-10** | Como **Autor de Contenido**, quiero **recibir una evaluación de la claridad pedagógica con observaciones**, para **saber si el paquete sirve tal cual o necesita revisión humana**. | FR-EVA-04, 05 |
| **US-11** | Como **Autor de Contenido**, quiero que **el sistema verifique que el contenido generado está anclado en el documento original y me reporte un puntaje de anclaje**, para **poder confiar en el material sin releer la fuente completa**. | FR-FID-01, 02 |
| **US-12** | Como **Sistema Externo Consumidor**, quiero **recibir un JSON estructurado y validado contra un esquema estricto**, para **integrarlo en mi plataforma sin parsear texto libre ni manejar respuestas impredecibles**. | FR-OUT-01, 02, 04 |
| **US-13** | Como **Equipo de Desarrollo**, quiero que **el documento técnico original quede persistido en el bucket Always Free de OCI Object Storage**, para **cumplir el requisito obligatorio de persistencia y conservar la fuente de cada paquete**. | FR-PER-01, 04, 05 |
| **US-14** | Como **Autor de Contenido**, quiero que **el JSON del paquete generado se almacene en OCI Object Storage y la respuesta me diga bucket, objeto y estado de la carga**, para **saber dónde quedó el artefacto y si la operación se completó**. | FR-PER-02, 03, 04, 05, 06 |
| **US-15** | Como **Autor de Contenido**, quiero **una interfaz donde cargue el documento, elija los parámetros y vea el paquete resultante**, para **usar el sistema sin escribir código ni llamadas HTTP**. | FR-UXA-01, 02 |
| **US-16** | Como **Sistema Externo Consumidor**, quiero **una acción/endpoint único de Adaptación de Contenido Educativo que reciba material y parámetros y devuelva el paquete completo**, para **automatizar la producción de contenido desde mis propios sistemas**. | FR-UXA-03, FR-OUT-01, 03 |
| **US-17** | Como **Autor de Contenido**, quiero **recibir mensajes de error claros cuando algo falla**, para **entender qué corregir en lugar de enfrentarme a una traza técnica o a una pantalla en blanco**. | FR-ERR-01, 02, 03 |
| **US-18** | Como **Evaluador del Hackathon**, quiero **un repositorio documentado con README, diagrama del flujo RAG/Agentes y los módulos o notebook de la pipeline**, para **verificar la implementación sin ejecutar el sistema**. | FR-DOC-01, 02, 05 |
| **US-19** | Como **Evaluador del Hackathon**, quiero **ver el mismo documento adaptado a al menos 2 perfiles y 2 formatos distintos, en al menos 3 escenarios**, para **comprobar que la personalización es real y no cosmética**. | FR-DOC-03, 06 |
| **US-20** | Como **Evaluador del Hackathon**, quiero **al menos 3 ejemplos de ejecución documentados con documentaciones reales o simuladas**, para **confirmar que el sistema funciona de extremo a extremo de forma reproducible**. | FR-DOC-04 |

---

## 6. Acceptance Criteria

Formato Given / When / Then. Cada criterio es **verificable por observación o por prueba**, sin requerir conocimiento de la implementación.

### US-01 — Carga de documento técnico

- **AC-01.1** — **Dado** un archivo PDF con contenido textual, **cuando** el Autor lo carga, **entonces** el sistema acepta el archivo y extrae su texto sin pedir ninguna preparación manual previa.
- **AC-01.2** — **Dado** un archivo Markdown, **cuando** el Autor lo carga, **entonces** el sistema acepta el archivo y extrae su contenido.
- **AC-01.3** — **Dado** un archivo de texto plano, **cuando** el Autor lo carga, **entonces** el sistema acepta el archivo y extrae su contenido.
- **AC-01.4** — **Dado** un archivo de formato no soportado, **cuando** el Autor lo carga, **entonces** el sistema lo rechaza con un mensaje que nombra los formatos admitidos, y **no** inicia el flujo de generación.
- **AC-01.5** — **Dado** un archivo soportado del que no se puede extraer texto (vacío o ilegible), **cuando** el Autor lo carga, **entonces** el sistema lo rechaza indicando que no se obtuvo contenido legible, y **no** consume llamadas al LLM.

### US-02 — Ingesta de contenido embebido en la solicitud

- **AC-02.1** — **Dada** una solicitud con `documento_titulo` y `documento_contenido` no vacíos y los parámetros de adaptación válidos, **cuando** se invoca la acción principal, **entonces** el sistema procesa el contenido y devuelve el paquete educativo completo.
- **AC-02.2** — **Dada** una solicitud con `documento_contenido` ausente o vacío, **cuando** se invoca la acción principal, **entonces** el sistema responde con un error de validación tipificado y **no** invoca al LLM.
- **AC-02.3** — **Dada** una solicitud que cumple el contrato de entrada documentado `(p.4)`, **cuando** se procesa, **entonces** ningún campo del contrato es ignorado silenciosamente.

### US-03 — Indexación RAG del documento

- **AC-03.1** — **Dado** un documento ingerido, **cuando** se ejecuta la indexación, **entonces** el sistema produce más de un chunk para un documento que excede el tamaño de fragmento configurado.
- **AC-03.2** — **Dado** el conjunto de chunks, **cuando** se ejecuta la vectorización, **entonces** existe un embedding asociado a cada chunk.
- **AC-03.3** — **Dados** los embeddings generados, **cuando** finaliza la indexación, **entonces** el Vector Store responde consultas de similitud sobre ese documento.
- **AC-03.4** — **Dado** un documento ingerido, **cuando** se registra, **entonces** tiene un identificador único que permite vincularlo con su paquete generado y con sus objetos en OCI.

### US-04 — Generación fundamentada en la fuente

- **AC-04.1** — **Dada** una solicitud de adaptación, **cuando** se ejecuta el flujo, **entonces** se recupera al menos un chunk del documento y ese contexto se entrega al flujo de generación.
- **AC-04.2** — **Dado** un chunk recuperado, **cuando** se inspecciona, **entonces** conserva su `document_id` y su referencia de origen (página o sección) dentro del documento.
- **AC-04.3** — **Dado** un documento que **no** contiene un concepto determinado, **cuando** se genera el paquete, **entonces** el contenido generado no afirma ese concepto como si proviniera del documento. *(Verificación manual sobre un documento de prueba controlado.)*

### US-05 — Parametrización de la adaptación

- **AC-05.1** — **Dado** el formulario o el contrato de entrada, **cuando** el Autor consulta las opciones, **entonces** están disponibles los 4 perfiles, los 5 formatos y los 4 nichos definidos en el documento fuente.
- **AC-05.2** — **Dado** un valor de parámetro fuera del conjunto permitido, **cuando** se envía la solicitud, **entonces** el sistema la rechaza con un error de validación que indica el campo y los valores admitidos, **antes** de consumir cuota de LLM.
- **AC-05.3** — **Dada** una combinación válida de perfil, formato y nicho, **cuando** se procesa, **entonces** los tres parámetros influyen efectivamente en el flujo de generación (verificable por AC-06.1, AC-07.1 y AC-08.1).

### US-06 — Adaptación al perfil

- **AC-06.1** — **Dado** un mismo documento y un mismo formato, **cuando** se genera para el perfil `Principiante / Transición de Carrera` y para el perfil `Líder Técnico / Arquitecto`, **entonces** los dos paquetes resultantes difieren de forma observable en vocabulario y profundidad, no sólo en el campo `perfil_aplicado`.
- **AC-06.2** — **Dado** el perfil `Gestor / Ejecutivo (No Técnico)`, **cuando** se genera el paquete, **entonces** el contenido evita jerga técnica no explicada.
- **AC-06.3** — **Dado** cualquier perfil válido, **cuando** se ejecuta el flujo, **entonces** se recorren las etapas de planificación, redacción y revisión antes de emitir el resultado.

### US-07 — Ejemplificación por nicho

- **AC-07.1** — **Dado** un mismo documento, perfil y formato, **cuando** se genera con nicho `Fintech` y con nicho `Salud`, **entonces** los ejemplos o analogías del contenido difieren y corresponden al sector seleccionado.
- **AC-07.2** — **Dado** el nicho `General`, **cuando** se genera el paquete, **entonces** los ejemplos no asumen ningún sector específico.

### US-08 — Estructuración según el formato

- **AC-08.1** — **Dado** un mismo documento y perfil, **cuando** se genera con formato `Flashcards de Memorización` y con formato `Guía Práctica Paso a Paso (Tutorial)`, **entonces** la estructura de `contenido_adaptado.items[]` es distinta y corresponde al formato solicitado en cada caso.
- **AC-08.2** — **Dado** el formato `Flashcards de Memorización`, **cuando** se genera el paquete, **entonces** cada ítem contiene `frente`, `dorso` y `pista_didactica`, conforme al contrato documentado `(p.5)`.
- **AC-08.3** — **Dado** cualquier formato válido, **cuando** se genera el paquete, **entonces** `contenido_adaptado` incluye `titulo` e `introduccion_contextualizada` no vacíos.
- **AC-08.4** — **Dado** cualquier formato válido, **cuando** se valida la salida, **entonces** `items[]` cumple el esquema tipado definido para **ese** formato y la validación falla si no lo cumple.
  - ⚠ **Bloqueado por A-08 / Q-08:** este criterio no es verificable para los 4 formatos cuya estructura aún no está definida.

### US-09 — Metadatos de aprendizaje

- **AC-09.1** — **Dado** un paquete generado, **cuando** se inspecciona la respuesta, **entonces** `metadatos.conceptos_clave` es una lista no vacía de términos presentes en el dominio del documento.
- **AC-09.2** — **Dado** un paquete generado, **cuando** se inspecciona la respuesta, **entonces** `metadatos.tiempo_estimado_estudio_minutos` es un entero positivo.
- **AC-09.3** — **Dado** un paquete generado, **cuando** se inspecciona la respuesta, **entonces** `metadatos.perfil_aplicado` y `metadatos.formato_generado` coinciden exactamente con los parámetros enviados en la solicitud.

### US-10 — Evaluación pedagógica

- **AC-10.1** — **Dado** un paquete generado, **cuando** se inspecciona la respuesta, **entonces** `evaluacion_calidad.claridad_pedagogica` contiene un valor de la escala definida por el equipo.
- **AC-10.2** — **Dado** un paquete generado, **cuando** se inspecciona la respuesta, **entonces** `evaluacion_calidad.observaciones` contiene un texto que justifica la evaluación y hace referencia al perfil aplicado.

### US-11 — Verificación de fidelidad

- **AC-11.1** — **Dado** un paquete generado, **cuando** se inspecciona la respuesta, **entonces** `evaluacion_calidad.anclaje_fuente_score` está presente y dentro del rango definido por el equipo.
- **AC-11.2** — **Dado** un documento de prueba y un paquete generado, **cuando** se ejecuta el mecanismo de verificación, **entonces** el puntaje se calcula contrastando el contenido generado contra los chunks recuperados, y **no** es un valor fijo ni una autoevaluación no verificable del modelo redactor.
- **AC-11.3** — **Dado** un paquete deliberadamente contaminado con una afirmación ajena al documento, **cuando** se ejecuta la verificación, **entonces** el puntaje resultante es menor que el del mismo paquete sin contaminar. *(Prueba de sensibilidad: demuestra que el mecanismo mide algo real.)*

### US-12 — Salida estructurada y validada

- **AC-12.1** — **Dada** una ejecución exitosa, **cuando** se devuelve la respuesta, **entonces** el JSON contiene las cinco secciones documentadas: `status`, `metadatos`, `contenido_adaptado`, `evaluacion_calidad`, `almacenamiento_oci`.
- **AC-12.2** — **Dada** una ejecución exitosa, **cuando** se devuelve la respuesta, **entonces** `status` toma el valor de éxito documentado (`"exito"`).
- **AC-12.3** — **Dada** una respuesta candidata que no cumple el esquema, **cuando** se valida antes de devolverla, **entonces** la validación falla y el sistema **no** entrega una salida malformada al consumidor.
- **AC-12.4** — **Dada** cualquier respuesta devuelta, **cuando** se parsea como JSON, **entonces** el parseo tiene éxito sin limpieza ni post-procesamiento manual.

### US-13 — Persistencia del documento original

- **AC-13.1** — **Dado** un documento ingerido, **cuando** finaliza la operación, **entonces** el documento original existe como objeto en el bucket de OCI Object Storage.
- **AC-13.2** — **Dado** el bucket utilizado, **cuando** se revisa su configuración, **entonces** pertenece a la capa Always Free y no genera cargos.
- **AC-13.3** — **Dado** un objeto persistido, **cuando** se inspecciona su nombre, **entonces** permite identificar el documento de origen y los parámetros aplicados.

### US-14 — Persistencia del paquete generado

- **AC-14.1** — **Dado** un paquete generado y validado, **cuando** finaliza la operación con éxito, **entonces** el JSON existe como objeto en el mismo bucket de OCI Object Storage.
- **AC-14.2** — **Dada** una carga exitosa, **cuando** se inspecciona la respuesta, **entonces** `almacenamiento_oci` reporta `bucket`, `objeto_id` y `status_upload` con valores reales correspondientes al objeto efectivamente creado.
- **AC-14.3** — **Dado** un objeto reportado en `almacenamiento_oci.objeto_id`, **cuando** se busca en el bucket, **entonces** existe y su contenido coincide con la respuesta devuelta.
- **AC-14.4** — **Dado** un fallo de carga a OCI, **cuando** se devuelve la respuesta, **entonces** `status` y `status_upload` reflejan el fallo de forma coherente con la política definida por el equipo.
  - ⚠ **Bloqueado por A-12 / Q-14:** la política aún no está decidida.

### US-15 — Interfaz de uso

- **AC-15.1** — **Dado** el sistema en ejecución, **cuando** el Autor abre la interfaz, **entonces** puede cargar un documento y seleccionar perfil, formato y nicho sin escribir código.
- **AC-15.2** — **Dada** una generación completada, **cuando** el Autor observa la interfaz, **entonces** ve el contenido adaptado, los metadatos de aprendizaje y la evaluación de calidad en forma legible.
- **AC-15.3** — **Dada** una generación fallida, **cuando** el Autor observa la interfaz, **entonces** ve un mensaje de error comprensible y la interfaz permanece utilizable.

### US-16 — Acción principal para integración

- **AC-16.1** — **Dada** una solicitud conforme al contrato de entrada, **cuando** se invoca la acción principal, **entonces** devuelve el paquete educativo completo conforme al contrato de salida, en una sola invocación.
- **AC-16.2** — **Dada** la misma solicitud lógica enviada por la interfaz y por la acción principal, **cuando** se comparan los resultados, **entonces** ambos producen paquetes con la misma estructura de contrato.

### US-17 — Errores comprensibles

- **AC-17.1** — **Dado** un fallo en cualquier etapa (ingesta, indexación, LLM, persistencia), **cuando** se informa al usuario, **entonces** el mensaje describe qué ocurrió y qué puede hacer, sin exponer trazas de excepción.
- **AC-17.2** — **Dado** un fallo de un servicio externo, **cuando** se produce, **entonces** el sistema no queda en un estado colgado ni sin respuesta.
- **AC-17.3** — **Dado** un fallo devuelto por la acción principal, **cuando** se inspecciona la respuesta, **entonces** tiene una estructura JSON estable y tipada.
  - ⚠ **Bloqueado parcialmente por A-15 / Q-12:** el contrato de error no está documentado en la fuente.

### US-18 — Auditoría del repositorio

- **AC-18.1** — **Dado** el repositorio, **cuando** el Evaluador lo abre, **entonces** encuentra un README con la arquitectura de la solución, un diagrama del flujo RAG/Agentes y una guía de instalación.
- **AC-18.2** — **Dado** el repositorio, **cuando** el Evaluador revisa el historial, **entonces** encuentra commits claros y evidencia de trabajo colaborativo.
- **AC-18.3** — **Dado** el repositorio, **cuando** el Evaluador busca la pipeline, **entonces** encuentra el notebook o los módulos con ingestión, chunking, embeddings, vector store, prompts, orquestación y verificación de fidelidad.
- **AC-18.4** — **Dada** la guía de instalación, **cuando** se sigue paso a paso en un entorno limpio, **entonces** el sistema queda operativo.

### US-19 — Evidencia de personalización

- **AC-19.1** — **Dado** un mismo documento técnico, **cuando** el Evaluador revisa la demostración, **entonces** ve al menos 3 escenarios distintos de adaptación sobre ese documento.
- **AC-19.2** — **Dados** esos escenarios, **cuando** se comparan, **entonces** cubren al menos 2 perfiles diferentes y al menos 2 formatos distintos.
- **AC-19.3** — **Dados** dos paquetes del mismo documento con perfiles distintos, **cuando** se comparan sus contenidos, **entonces** la diferencia es sustantiva y perceptible sin necesidad de leer los metadatos.

### US-20 — Ejemplos de ejecución

- **AC-20.1** — **Dado** el entregable, **cuando** el Evaluador lo revisa, **entonces** encuentra al menos 3 ejemplos de ejecución documentados con su entrada, su salida JSON y su evidencia de persistencia en OCI.
- **AC-20.2** — **Dado** un ejemplo documentado, **cuando** se reproduce siguiendo el repositorio, **entonces** el sistema produce un paquete de la misma estructura.

---

## 7. End-to-End Use Cases

### UC-01 · Adaptación desde documento cargado *(flujo principal)*

**Actor:** A1 · **Precondición:** sistema operativo, bucket Always Free creado, credenciales configuradas.

```
A1 carga documento (PDF/MD/TXT)
        │
        ▼
[D1] Validar formato y tamaño ──── falla ──► UC-05
        │
        ▼
[D1] Extraer texto · normalizar · asignar document_id
        │
        ▼
[D8] Persistir documento original en OCI Object Storage        (FR-PER-01)
        │
        ▼
[D2] Chunking ──► Embeddings ──► Vector Store                  (FR-RAG-01/02/03)
        │
        ▼
A1 selecciona Perfil + Formato + Nicho
        │
        ▼
[D3] Validar parámetros contra conjuntos permitidos ─ falla ─► UC-05
        │
        ▼
[D2] Recuperar chunks relevantes                               (FR-RAG-04)
        │
        ▼
[D4] ORQUESTACIÓN: planificar ──► redactar ──► revisar          (FR-GEN-01)
        │                          (prompts few-shot + role prompting)
        ▼
[D5] Evaluación pedagógica: conceptos clave · tiempo · claridad (FR-EVA-*)
        │
        ▼
[D6] Verificación de fidelidad ──► anclaje_fuente_score         (FR-FID-01/02)
        │
        ├─ score < umbral ──► UC-04
        ▼
[D7] Componer y validar JSON contra esquema estricto            (FR-OUT-01/02)
        │
        ▼
[D8] Persistir JSON del paquete en OCI ──► bucket, objeto_id    (FR-PER-02/03)
        │
        ├─ falla ──► UC-06
        ▼
[D7] Devolver respuesta  +  [D9] Renderizar en la interfaz
```

**Postcondición:** dos objetos en el bucket (documento original + JSON del paquete); un JSON válido entregado al Autor.
**Fuente:** composición de `[EXP] (p.1-5)`. El orden relativo de la persistencia del documento original respecto a la indexación es `[INF]` — ver §11 Q-17.

---

### UC-02 · Adaptación desde texto embebido *(vía acción principal / API)*

**Actor:** S1 o A1 · **Diferencia con UC-01:** no hay archivo; el material llega en `documento_contenido`.

```
Solicitud JSON { documento_titulo, documento_contenido, perfil_destinatario,
                 formato_salida, nicho_sector, nivel_detalle }
        │
        ▼
[D7] Validar contrato de entrada (tipado estricto) ─ falla ─► respuesta de error tipificada
        │
        ▼
[D1] Tratar documento_contenido como texto ingerido · document_id
        │
        ▼
  ═══ idéntico a UC-01 desde la persistencia del original ═══
        │
        ▼
Respuesta JSON completa al consumidor
```

**Fuente:** `[EXP] (p.4)` — es el único contrato de invocación documentado.
**⚠ Depende de A-01 / Q-01:** si UC-01 y UC-02 son el mismo endpoint con dos modos de entrada, o dos superficies distintas, está sin decidir.

---

### UC-03 · Multi-adaptación comparativa *(cumple el Checklist casilla 4 y 7)*

**Actor:** A1, A4 · **Objetivo:** demostrar personalización real sobre un mismo documento.

```
Documento único ingerido e indexado UNA vez
        │
        ├──► Escenario 1: Principiante  × Flashcards        ──► Paquete 1 ──► OCI
        ├──► Escenario 2: Líder Técnico × Tutorial          ──► Paquete 2 ──► OCI
        └──► Escenario 3: Gestor/Ejecutivo × Resumen (TL;DR)──► Paquete 3 ──► OCI
                    │
                    ▼
        Comparación lado a lado (FR-UXA-06)
                    │
                    ▼
        Evidencia: ≥3 escenarios · ≥2 perfiles · ≥2 formatos
```

**Nota de diseño `[INF]`:** este flujo es el que hace que **FR-RAG-07 (ciclo de vida del índice, A-02)** importe de verdad. Si el índice es efímero por solicitud, los 3 escenarios re-indexan el mismo documento 3 veces: 3× costo de embeddings y 3× latencia en plena demostración.

---

### UC-04 · Fidelidad por debajo del umbral

```
[D6] anclaje_fuente_score < umbral
        │
        ▼
Acción correctiva definida por el equipo:
        ├─ (a) Regenerar con contexto ampliado y reintentar (n acotado)
        ├─ (b) Entregar el paquete MARCADO como de baja fidelidad
        └─ (c) Rechazar la generación con error tipificado
```

**Estado:** `[INF]` · **bloqueado por A-10 y A-11 → Q-10, Q-11.** El documento exige el mecanismo pero **no define qué hacer con su resultado**. Sin esta decisión, la anti-alucinación es un reporte, no un control.

---

### UC-05 · Entrada inválida

```
Archivo no soportado / vacío / ilegible  ó  parámetro fuera de enum
        │
        ▼
[D10] Capturar y tipificar el error         (FR-ERR-02)
        │
        ▼
[D10] Mensaje amigable y accionable         (FR-ERR-01)
        │
        ▼
Respuesta de error con contrato estable     (FR-ERR-03)
        │
        ▼
SIN consumo de LLM · SIN escritura en OCI · interfaz sigue utilizable
```

**Fuente:** `[EXP] (p.3)`; la garantía de no consumo de LLM antes de validar es `[INF]` (protege la cuota gratuita — ver R-05).

---

### UC-06 · Fallo de persistencia en OCI

```
Carga a Object Storage falla (red, credenciales, permisos, cuota)
        │
        ▼
        ¿Política definida?  ──► ⚠ PENDIENTE (A-12 / Q-14)
        │
        ├─ (a) OCI en ruta crítica  ──► status de error; no se entrega el paquete
        └─ (b) Degradación controlada ──► se entrega el paquete con
                                          status_upload = fallido
```

**Impacto en la demostración:** si se elige (a) y la red falla durante la presentación, se pierde la demo completa aunque la generación haya funcionado. Ver R-06.

---

### UC-07 · Quiz interactivo en tiempo real `[OPCIONAL]`

```
Paquete con formato "Quiz Interactivo con Justificaciones"
        │
        ▼
A2 (Estudiante) responde en la interfaz
        │
        ▼
Retroalimentación explicativa inmediata basada en la justificación generada
```

**Fuente:** `[EXP] (p.6)` — diferencial opcional. **Único caso en que A2 opera el sistema.**

---

### UC-08 · Exportación multiformato `[OPCIONAL]`

```
Paquete generado ──► Exportar a: Markdown · PDF didáctico · CSV compatible con Anki
```

**Fuente:** `[EXP] (p.6)` — diferencial opcional.
---

## 8. MVP

> **Criterio de corte aplicado:** entra al MVP lo que el **Checklist de Evaluación `(p.5-6)`** exige, más lo que sea materialmente imprescindible para que esas casillas sean verdaderas. Todo lo demás queda fuera, por interesante que sea.

### 8.1 MUST HAVE — MVP obligatorio

| Dominio | Requisitos | Justificación de corte |
|---|---|---|
| **D1 Ingestión** | FR-ING-01, 02, 03, 04, 06, 07 | Checklist casilla 1 + contrato de entrada oficial `(p.4)` |
| **D2 RAG** | FR-RAG-01, 02, 03, 04, 06 | Checklist casilla 2. FR-RAG-06 entra porque sin trazabilidad de chunk, D6 no es verificable |
| **D3 Parametrización** | FR-PAR-01, 02, 03, 05 | Los 3 ejes de parametrización son el valor del producto `(p.1-2)` |
| **D4 Generación** | FR-GEN-01, 02, 03, 04, 05, 06, 07 | Checklist casillas 3 y 4 + Resultados esperados `(p.3)` |
| **D5 Evaluación pedagógica** | FR-EVA-01, 02, 04, 05, 06 | Objetivo 4 `(p.3)` + contrato de salida `(p.5)` |
| **D6 Fidelidad** | FR-FID-01, 02 | Exigido explícitamente `(p.2, p.3, p.5)`. **Es el diferenciador declarado del producto** |
| **D7 Contrato** | FR-OUT-01, 02, 03, 04, 05 | Checklist casilla 5 + tipado estricto `(p.3, p.6)` |
| **D8 Persistencia OCI** | FR-PER-01, 02, 03, 04, 05, 06 *(decisión)* | Checklist casilla 6. **Requisito obligatorio, sin sustituto** |
| **D9 Interfaz / API** | FR-UXA-01, 02, 03 | Checklist casilla 5 + Funcionalidades obligatorias `(p.4)` |
| **D10 Errores** | FR-ERR-01, 02, 03 | Resultados esperados `(p.3)` |
| **D11 Evidencia** | FR-DOC-01, 02, 03, 04, 05, 06 | **Checklist casillas 4, 7 y 8 — 3 de las 8 casillas** |

**Total MVP: 52 requisitos `MUST`, distribuidos en 11 dominios, cubiertos por 20 User Stories y 63 criterios de aceptación.**

> ⚠ **Advertencia de planificación:** D11 no es "documentar al final". Tres de las ocho casillas del Checklist se evalúan allí. Un sistema que funciona perfecto y llega sin README, sin diagrama y sin 3 ejemplos documentados pierde **37,5% de la evaluación mínima**. Ver R-10.

### 8.2 SHOULD HAVE — dentro del MVP si el tiempo lo permite

Alto valor, no bloquean ninguna casilla del Checklist:

| ID | Requisito | Por qué vale la pena |
|---|---|---|
| FR-UXA-06 | Comparación de escenarios lado a lado | Convierte el requisito de evaluación (casilla 4 y 7) en una **capacidad visible del producto**. Mejor retorno por esfuerzo de toda la lista |
| FR-FID-03 | Umbral de fidelidad y acción correctiva | Convierte el puntaje de anclaje en un **control** real, no en un reporte |
| FR-GEN-08 | Recuperación ante salida no parseable | Protege el requisito `MUST` de tipado estricto frente a la no-determinación del LLM |
| FR-ING-05 | Normalización del texto extraído | Calidad de todo lo que viene después; mitiga R-12 |
| FR-EVA-03 | Prerrequisitos | Exigido en `(p.2)`; ver A-09 |
| FR-UXA-04 | Acceso al JSON crudo desde la interfaz | Evidencia directa de la casilla 5 ante el evaluador |
| FR-RAG-05 | Construcción de la consulta de recuperación | Determina la calidad del contexto recuperado |
| FR-RAG-07 | Ciclo de vida del índice | Impacto directo en costo y latencia de UC-03 |
| FR-PAR-04 | `nivel_detalle` | Aparece en el contrato de entrada oficial `(p.4)` |
| FR-PAR-06 | Obligatoriedad y valores por defecto | Robustez del contrato |
| FR-UXA-05 | Indicación de progreso | Usabilidad durante una cadena de varios segundos |
| FR-ERR-04 | Degradación controlada | Depende de Q-14 |
| FR-ERR-05 | Timeouts y reintentos | Evita bloqueos en la demostración |

### 8.3 NICE TO HAVE — diferenciales, fuera del MVP

Todos son **opcionales según el documento fuente `(p.4, p.6)`**. Ninguno se compromete en esta fase.

| ID | Diferencial | Fuente |
|---|---|---|
| FR-OPT-01 | Despliegue completo en OCI Compute (VM Linux Always Free) | `[EXP] (p.4, p.6)` |
| FR-GEN-09 / FR-OPT-02 | Sistema multi-agente con enrutador (Investigador RAG · Redactor · Crítico) | `[EXP] (p.6)` |
| FR-UXA-07 / FR-OPT-03 | Quiz con evaluación y retroalimentación en tiempo real | `[EXP] (p.6)` |
| FR-OPT-04 | Soporte multimodal (interpretación de diagramas técnicos) | `[EXP] (p.6)` |
| FR-OPT-05 | Exportación multiformato (Markdown / PDF didáctico / CSV Anki) | `[EXP] (p.6)` |
| FR-FID-04 | Citación de fragmentos fuente por ítem generado | `[PROP]` — haría auditable el `anclaje_fuente_score` |
| FR-GEN-10 | Reproducibilidad de la generación | `[PROP]` — mitiga R-09, costo casi nulo |
| FR-RAG-08 | Re-ranking de chunks recuperados | `[PROP]` |
| FR-OUT-06 | Versionado del esquema de salida | `[PROP]` |
| FR-PER-07 | Listado/recuperación de paquetes generados | `[PROP]` |

### 8.4 OUT OF SCOPE — explícitamente fuera

| ID | Excluido | Razón |
|---|---|---|
| FR-UXA-08 | Autenticación y gestión de usuarios | No mencionado en ninguna parte del documento |
| FR-UXA-09 | Historial de generaciones por usuario | No respaldado; requiere autenticación |
| FR-ING-08 | OCR de documentos escaneados | No respaldado; lo adyacente (multimodal) es opcional |
| FR-PER-08 | Persistencia del índice vectorial en OCI | El documento delimita el uso obligatorio a documentos originales y JSON generados `(p.4)` |
| — | Edición manual del contenido generado | No respaldado |
| — | Colaboración multiusuario / roles | No respaldado |
| — | Analítica de aprendizaje del estudiante | No respaldado; A2 no opera el sistema en el MVP |
| — | Soporte de formatos de entrada adicionales (DOCX, HTML, URL) | El documento fija PDF, Markdown y texto `(p.1)` |
| — | Cualquier recurso de OCI fuera de la capa Always Free | Prohibido explícitamente `(p.4, p.7)` |

---

## 9. Requirements Traceability Matrix

### 9.1 Checklist de Evaluación → cobertura completa

| # | Requisito del Hackathon `(p.5-6)` | Functional Requirements | User Stories | Acceptance Criteria | Estado |
|---|---|---|---|---|---|
| **H-01** | Ingestión funcional de documentos técnicos (PDF, Markdown o texto) | FR-ING-01, 02, 03, 04, 06, 07 | US-01, US-02 | AC-01.1 → 01.5, AC-02.1 → 02.3, AC-03.4 | ✅ Cubierto · ⚠ depende Q-01 |
| **H-02** | RAG con chunking, embeddings y búsqueda vectorial en Vector Store | FR-RAG-01, 02, 03, 04, 06 | US-03, US-04 | AC-03.1 → 03.3, AC-04.1 → 04.3 | ✅ Cubierto |
| **H-03** | Orquestación con LLM | FR-GEN-01, 02, 03 | US-06 | AC-06.1 → 06.3, AC-18.3 | ✅ Cubierto |
| **H-04** | Adaptar el mismo contenido a ≥2 perfiles y ≥2 formatos | FR-PAR-01, 02; FR-GEN-03, 05, 07; FR-DOC-06 | US-05, US-06, US-08, US-19 | AC-05.1, AC-06.1, AC-08.1, AC-19.2, AC-19.3 | ✅ Cubierto · ⚠ depende Q-08 |
| **H-05** | Salida JSON estructurada **e** interfaz interactiva **o** API REST operativa | FR-OUT-01, 02, 03, 04, 05; FR-UXA-01, 02, 03 | US-12, US-15, US-16 | AC-12.1 → 12.4, AC-15.1 → 15.3, AC-16.1, AC-16.2 | ✅ Cubierto · ⚠ depende Q-15 |
| **H-06** | Integración activa y funcional con OCI Object Storage (Always Free) | FR-PER-01, 02, 03, 04, 05, 06 | US-13, US-14 | AC-13.1 → 13.3, AC-14.1 → 14.4 | ✅ Cubierto · ⚠ depende Q-14 |
| **H-07** | Mínimo 3 ejemplos de ejecución con documentaciones reales o simuladas | FR-DOC-03, 04 | US-19, US-20 | AC-19.1, AC-20.1, AC-20.2 | ✅ Cubierto · ⚠ depende Q-16 |
| **H-08** | Documentación completa en GitHub con diagrama de arquitectura | FR-DOC-01, 02, 05 | US-18 | AC-18.1 → 18.4 | ✅ Cubierto |

### 9.2 Requisitos del cuerpo del documento no incluidos en el Checklist

Estos **no aparecen en las 8 casillas** pero sí son exigidos en el texto. Se rastrean para que no se pierdan.

| # | Requisito | Fuente | Functional Requirements | User Stories | Acceptance Criteria | Estado |
|---|---|---|---|---|---|---|
| **H-09** | Metadatos de aprendizaje: conceptos clave y tiempo estimado de estudio | `(p.2, p.3, p.5)` | FR-EVA-01, 02, 06 | US-09 | AC-09.1 → 09.3 | ✅ Cubierto |
| **H-10** | Metadatos de aprendizaje: **prerrequisitos** | `(p.2)` | FR-EVA-03 `SHOULD` | — | — | ⚠ **BRECHA** · exigido en `(p.2)`, ausente del contrato `(p.5)` → Q-09 |
| **H-11** | Evaluación de coherencia didáctica | `(p.2, p.3, p.5)` | FR-EVA-04, 05 | US-10 | AC-10.1, AC-10.2 | ✅ Cubierto |
| **H-12** | Mecanismo de verificación de fidelidad para mitigar alucinaciones | `(p.2, p.3, p.5)` | FR-FID-01, 02 | US-11 | AC-11.1 → 11.3 | ✅ Cubierto · ⚠ depende Q-10, Q-11 · riesgo R-02 |
| **H-13** | Prompts estructurados con few-shot y role prompting | `(p.3)` | FR-GEN-02 | US-06, US-18 | AC-18.3 *(verificación por inspección del notebook/módulos)* | ⚠ **Verificable sólo por inspección**, no por comportamiento observable |
| **H-14** | Validación de esquemas de entrada y salida con tipado estricto | `(p.3, p.6)` | FR-OUT-02, 03; FR-PAR-05 | US-05, US-12 | AC-05.2, AC-12.3 | ✅ Cubierto |
| **H-15** | Manejo de excepciones y mensajes de error amigables | `(p.3)` | FR-ERR-01, 02, 03 | US-17 | AC-17.1 → 17.3 | ✅ Cubierto · ⚠ depende Q-12 |
| **H-16** | Ejemplificación contextualizada al nicho (4 nichos) | `(p.2)` | FR-PAR-03, FR-GEN-04 | US-05, US-07 | AC-05.1, AC-07.1, AC-07.2 | ✅ Cubierto · ⚠ depende Q-03 |
| **H-17** | Cobertura de los **4 perfiles** y los **5 formatos** definidos | `(p.1, p.2)` | FR-PAR-01, 02; FR-GEN-07; FR-OUT-05 | US-05, US-08 | AC-05.1, AC-08.1 → 08.4 | ⚠ **En riesgo** · el Checklist sólo exige 2×2, pero el documento define 4×5 → Q-08 |
| **H-18** | 3 escenarios de adaptación sobre **un mismo** documento | `(p.4)` | FR-DOC-03 | US-19 | AC-19.1 | ✅ Cubierto · ⚠ depende Q-16 |
| **H-19** | Flujo con etapas de planificar, redactar y revisar | `(p.3)` | FR-GEN-01 | US-06 | AC-06.3 | ✅ Cubierto |
| **H-20** | Salida integrable con sistemas externos | `(p.2)` | FR-OUT-01, FR-UXA-03 | US-12, US-16 | AC-12.1, AC-16.1, AC-16.2 | ✅ Cubierto |
| **H-21** | Uso exclusivo de la capa Always Free de OCI | `(p.4, p.7)` | FR-PER-05 | US-13 | AC-13.2 | ✅ Cubierto · ⚠ no cubre el costo del LLM → R-05 |
| **H-22** | Repositorio con commits claros y colaborativos | `(p.4)` | FR-DOC-01 | US-18 | AC-18.2 | ✅ Cubierto |
| **H-23** | Notebook o módulos con la pipeline | `(p.3)` | FR-DOC-05 | US-18 | AC-18.3 | ✅ Cubierto |

### 9.3 Resumen de auditoría de cobertura

| Verificación | Resultado |
|---|---|
| Casillas del Checklist sin FR asignado | **0** |
| Casillas del Checklist sin User Story | **0** |
| Casillas del Checklist sin Acceptance Criteria | **0** |
| FR `MUST` sin User Story | **0** |
| User Stories sin Acceptance Criteria | **0** |
| Requisitos del cuerpo del documento sin cobertura `MUST` | **1** → H-10 (prerrequisitos) |
| Acceptance Criteria bloqueados por una ambigüedad sin resolver | **3** → AC-08.4, AC-14.4, AC-17.3 |
| Requisitos verificables sólo por inspección de código | **1** → H-13 |

---

## 10. Non-Functional Requirements

> **Regla aplicada:** ningún valor numérico se inventa. Donde el documento no especifica, dice **`TBD (equipo)`**.

### 10.1 Performance

| ID | Requisito | Valor | Fuente |
|---|---|---|---|
| NFR-PRF-01 | Tiempo total de una adaptación extremo a extremo | **Orden de minutos, no de horas.** Valor objetivo: `TBD (equipo)` | `[EXP] (p.2)` — único anclaje: "de semanas a minutos"; "instantáneamente"; "unos pocos clics" |
| NFR-PRF-02 | Tiempo de ingestión e indexación de un documento | `TBD (equipo)` | No especificado |
| NFR-PRF-03 | Tamaño máximo de documento admitido | `TBD (equipo)` | No especificado — condiciona FR-ING-06 |
| NFR-PRF-04 | Solicitudes concurrentes soportadas | `TBD (equipo)` | No especificado. **Nota:** el documento no describe uso multiusuario |
| NFR-PRF-05 | Latencia aceptable en la demostración en vivo | `TBD (equipo)` | `[INF]` — restricción de presentación, no de producto. Ver R-11 |

### 10.2 Reliability

| ID | Requisito | Valor | Fuente |
|---|---|---|---|
| NFR-REL-01 | Toda excepción en la cadena (ingesta, embeddings, LLM, OCI) es capturada y tipificada | Obligatorio | `[EXP] (p.3)` |
| NFR-REL-02 | El sistema nunca entrega una salida que no cumpla el esquema: o cumple, o falla explícitamente | Obligatorio | `[EXP] (p.3, p.6)` |
| NFR-REL-03 | Disponibilidad del servicio | `TBD (equipo)` | No especificado |
| NFR-REL-04 | Reproducibilidad de los escenarios de demostración | `TBD (equipo)` | `[INF]` — requerido de hecho por FR-DOC-04. Ver R-09 |
| NFR-REL-05 | Ninguna operación queda en estado colgado o sin respuesta | Obligatorio | `[INF]` derivado de `[EXP] (p.3)` |

### 10.3 Security

| ID | Requisito | Valor | Fuente |
|---|---|---|---|
| NFR-SEC-01 | Las credenciales de OCI y de LLM **nunca** se versionan en el repositorio | Obligatorio | `[INF]` — el documento exige repositorio **GitHub** `(p.6)` y credenciales de OCI `(p.6)` en el mismo proyecto. Ver R-07 |
| NFR-SEC-02 | Los mensajes de error no exponen trazas técnicas, rutas ni secretos | Obligatorio | `[INF]` derivado de `[EXP] (p.3)` "mensajes de error amigables" |
| NFR-SEC-03 | Política de acceso del bucket (público / privado / URL pre-autenticada) | `TBD (equipo)` | No especificado · tensión con `(p.2)` "integración con sistemas externos" |
| NFR-SEC-04 | Autenticación de la interfaz o del endpoint | **No requerida** por el documento · `TBD (equipo)` si se despliega público (FR-OPT-01) | No especificado |
| NFR-SEC-05 | Tratamiento de documentos de terceros cargados por el usuario (retención, borrado) | `TBD (equipo)` | No especificado |

### 10.4 Maintainability

| ID | Requisito | Valor | Fuente |
|---|---|---|---|
| NFR-MNT-01 | La pipeline está expresada en notebook o módulos identificables e inspeccionables | Obligatorio | `[EXP] (p.3)` |
| NFR-MNT-02 | Los esquemas tipados son el contrato único entre capas | Obligatorio | `[EXP] (p.3, p.6)` |
| NFR-MNT-03 | Los prompts son artefactos identificables y modificables sin tocar la lógica del flujo | `[PROP]` | `[INF]` — el documento exige "optimización de prompts" `(p.3)`, lo que implica iteración |
| NFR-MNT-04 | El repositorio tiene estructura clara y commits legibles | Obligatorio | `[EXP] (p.4)` |

### 10.5 Scalability

| ID | Requisito | Valor | Fuente |
|---|---|---|---|
| NFR-SCA-01 | Volumen de documentos / usuarios soportado | `TBD (equipo)` · **techo real = límites de la capa Always Free** | No especificado |
| NFR-SCA-02 | El diseño no debe acoplarse a un proveedor de LLM específico | `SHOULD` | `[INF]` — el documento insiste en la libertad de elección de LLM y en la ausencia de exclusividad `(p.2, p.3, p.6)`. Mitiga R-13 |
| NFR-SCA-03 | Crecimiento del Vector Store con múltiples documentos | `TBD (equipo)` | Depende de Q-06 |

### 10.6 Cost

| ID | Requisito | Valor | Fuente |
|---|---|---|---|
| NFR-COS-01 | **Ningún recurso de OCI fuera de la capa Always Free** | **Obligatorio · restricción dura** | `[EXP] (p.4)` "Aviso Importante ONE"; `(p.7)` |
| NFR-COS-02 | Costo de las llamadas a LLM y a embeddings | `TBD (equipo)` — **no cubierto por la restricción Always Free** | ⚠ **Vacío del documento.** "Always Free" aplica a OCI; el documento permite LLMs de pago sin decir quién asume el costo. Ver R-05 y Q-20 |
| NFR-COS-03 | Consumo evitable de cuota de LLM ante entradas inválidas | Se valida **antes** de invocar al LLM | `[INF]` — ver AC-02.2, AC-05.2 |
| NFR-COS-04 | Costo de re-indexar el mismo documento en escenarios múltiples | `TBD (equipo)` | Depende de Q-06 · ver UC-03 |

### 10.7 Observability

| ID | Requisito | Valor | Fuente |
|---|---|---|---|
| NFR-OBS-01 | Registro de ejecuciones (entrada, parámetros, resultado) | `TBD (equipo)` | No especificado · **de hecho necesario** para FR-DOC-04 (3 ejemplos documentados) |
| NFR-OBS-02 | Trazabilidad de una generación: chunks usados, etapas ejecutadas, puntaje obtenido | `SHOULD` | `[INF]` — sin esto, un `anclaje_fuente_score` bajo no es diagnosticable |
| NFR-OBS-03 | Métrica de consumo de tokens por ejecución | `TBD (equipo)` | `[PROP]` — instrumento de control de NFR-COS-02 |

### 10.8 Data Validation

| ID | Requisito | Valor | Fuente |
|---|---|---|---|
| NFR-VAL-01 | Validación tipada estricta de **entrada** | Obligatorio | `[EXP] (p.3, p.6)` |
| NFR-VAL-02 | Validación tipada estricta de **salida** | Obligatorio | `[EXP] (p.3, p.6)` |
| NFR-VAL-03 | Los parámetros se validan contra conjuntos cerrados de valores | Obligatorio | `[INF]` derivado de `(p.1-2)` + `(p.3)` · depende Q-02 |
| NFR-VAL-04 | Nada se persiste en OCI antes de pasar la validación de salida | Obligatorio | `[INF]` — evita almacenar artefactos malformados |
| NFR-VAL-05 | La validación de entrada ocurre antes de cualquier consumo de servicio externo | Obligatorio | `[INF]` — ver NFR-COS-03 |

### 10.9 Error Handling

| ID | Requisito | Valor | Fuente |
|---|---|---|---|
| NFR-ERH-01 | Mensajes de error comprensibles y accionables para el usuario | Obligatorio | `[EXP] (p.3)` |
| NFR-ERH-02 | Contrato de error JSON estable y tipado | Obligatorio | `[INF]` · **forma sin definir** → Q-12 |
| NFR-ERH-03 | Timeouts y política de reintentos ante servicios externos | `TBD (equipo)` | `[INF]` |
| NFR-ERH-04 | Política de degradación ante fallo de persistencia | `TBD (equipo)` | `[INF]` → Q-14 |
| NFR-ERH-05 | La interfaz permanece utilizable tras un error | Obligatorio | `[INF]` derivado de `[EXP] (p.3)` |

---

## 11. Open Questions

### 11.1 Ambigüedades detectadas en el documento fuente

| ID | Ambigüedad | Ubicación |
|---|---|---|
| A-01 | Ingestión de **archivos** vs. contrato de entrada con **texto embebido** | `(p.1, p.3, p.5)` vs `(p.4)` |
| A-02 | Ciclo de vida del índice vectorial: efímero, por documento o acumulativo | `(p.2)` |
| A-03 | Forma canónica de los valores de perfil (`"Principiante"` vs `"Principiante / Transición de Carrera"`); lista cerrada o abierta ("ej.:") | `(p.1)` vs `(p.4)` |
| A-04 | Ídem para los valores de formato (`"Flashcards"` vs `"Flashcards de Memorización"`) | `(p.2)` vs `(p.4)` |
| A-05 | El nicho no se refleja en `metadatos` de la respuesta, a diferencia de perfil y formato | `(p.2)` vs `(p.5)` |
| A-06 | `nivel_detalle`: presente en el contrato de entrada, ausente de los criterios de parametrización, sin valores ni reflejo en la salida | `(p.4)` vs `(p.1-2, p.5)` |
| A-07 | Obligatoriedad de cada parámetro de la solicitud | `(p.4)` |
| A-08 | **Sólo se documenta la estructura de `items[]` para Flashcards; faltan 4 de 5 formatos** | `(p.2)` vs `(p.5)` |
| A-09 | `prerrequisitos` exigido en el cuerpo, ausente del contrato de salida | `(p.2)` vs `(p.5)` |
| A-10 | `anclaje_fuente_score`: sin escala, sin método de cálculo, sin semántica | `(p.5)` |
| A-11 | `almacenamiento_oci` reporta un solo `objeto_id`, pero se persisten dos artefactos | `(p.4)` vs `(p.5)` |
| A-12 | Política ante fallo de carga a OCI; existencia del campo `status_upload` implica que puede fallar | `(p.5)` |
| A-13 | Interfaz **o** API: disyunción en el Checklist, exigencia de endpoint en Funcionalidades obligatorias | `(p.3, p.4)` vs `(p.5)` |
| A-14 | "3 escenarios sobre un mismo documento" vs "3 ejemplos con documentaciones reales o simuladas" | `(p.4)` vs `(p.6)` |
| A-15 | El contrato de error no está documentado; sólo existe el ejemplo de éxito | `(p.4-5)` |
| A-16 | Agentes como roles lógicos obligatorios vs. agentes autónomos opcionales | `(p.3)` vs `(p.6)` |

### 11.2 Decisiones BLOQUEANTES — resolver antes de diseñar la arquitectura

| ID | Pregunta | Deriva de | Por qué bloquea |
|---|---|---|---|
| **Q-08** | **¿Cuál es la estructura de `items[]` para Tutorial, Quiz, TL;DR y Guion de Clase?** ¿Se implementan los 5 formatos o sólo los 2 que exige el Checklist? | A-08 | Define el contrato de salida completo, los prompts por formato y la validación tipada. **Es la decisión de mayor impacto de toda la lista.** |
| **Q-10** | ¿Qué mide exactamente `anclaje_fuente_score`, en qué escala, y calculado cómo? | A-10 | Es el diferenciador del producto. Si lo produce el mismo modelo que redactó, no es verificación (R-02) |
| **Q-11** | ¿Hay umbral mínimo de fidelidad? ¿Qué hace el sistema por debajo: regenerar, marcar o rechazar? | FR-FID-03 | Define si UC-04 existe y si el flujo tiene un lazo de realimentación |
| **Q-01** | ¿La entrada por archivo y la entrada por texto son el mismo endpoint con dos modos, dos endpoints, o la interfaz extrae y llama con texto? | A-01 | Define el contrato público y el límite entre UI y núcleo |
| **Q-14** | ¿OCI Object Storage está en la ruta crítica? ¿Un fallo de carga invalida la operación o se degrada? | A-12 | Define el comportamiento del contrato, el manejo de errores y el riesgo de la demostración (R-06) |
| **Q-15** | ¿Se entrega interfaz, API, o ambas? | A-13 | Define cuántas superficies hay que construir, probar y documentar |
| **Q-06** | ¿El índice vectorial es efímero por solicitud, persistente por documento, o acumulativo? | A-02 | Impacta costo, latencia y el flujo central UC-03 |

### 11.3 Decisiones de contrato — resolver junto con la arquitectura

| ID | Pregunta | Deriva de |
|---|---|---|
| Q-02 | ¿Cuál es la forma canónica de los valores de perfil y formato? ¿Las listas son cerradas? | A-03, A-04 |
| Q-03 | ¿`nicho_sector` se refleja en `metadatos` de la respuesta? | A-05 |
| Q-04 | ¿Se implementa `nivel_detalle`? Si sí: ¿qué valores, y cómo se relaciona con el perfil? | A-06 |
| Q-07 | ¿Qué parámetros son obligatorios? ¿Hay valores por defecto? | A-07 |
| Q-09 | ¿Se añade `prerrequisitos` a `metadatos`, o se acepta la omisión del contrato ejemplo? | A-09 |
| Q-12 | ¿Cuál es la forma del contrato de error y qué valores toma `status` al fallar? | A-15 |
| Q-13 | ¿Cómo se reportan **dos** objetos persistidos en una sección que sólo tiene un `objeto_id`? | A-11 |
| Q-05 | ¿Qué se usa como consulta de recuperación: el documento completo, sus secciones, o consultas derivadas de los parámetros? | FR-RAG-05 |
| Q-17 | ¿El documento original se persiste antes o después de la generación exitosa? | UC-01 |

### 11.4 Decisiones de alcance y entrega

| ID | Pregunta |
|---|---|
| Q-16 | ¿Los 3 escenarios y los 3 ejemplos son lo mismo? **Recomendación de esta especificación:** satisfacer ambas lecturas — 3 escenarios sobre un documento común **y** al menos un segundo documento distinto entre los ejemplos |
| Q-18 | ¿El equipo se compromete con algún diferencial opcional (§8.3)? Si sí, ¿cuál y con qué criterio de corte temporal? |
| Q-19 | ¿Se implementa el sistema multi-agente (FR-GEN-09) o basta la cadena con las tres responsabilidades lógicas? |
| Q-20 | **¿Quién asume el costo de las llamadas a LLM y embeddings, y con qué límite?** El "Always Free" del documento cubre OCI, no el LLM |
| Q-21 | ¿Cuál es el documento técnico de referencia para la demostración y los 3 escenarios? |
| Q-22 | ¿Cómo se reparte el trabajo en el equipo para que FR-DOC-01 (commits colaborativos) sea genuino y no un artificio? |

### 11.5 Decisiones que NO corresponden a esta fase

> Se listan **sólo para registrar que existen** y evitar que se resuelvan por inercia durante el diseño funcional. **No se decide ninguna aquí.**

| ID | Decisión | Fase |
|---|---|---|
| Q-23 | Proveedor y modelo de LLM | Arquitectura |
| Q-24 | Modelo de embeddings | Arquitectura |
| Q-25 | Vector Store | Arquitectura |
| Q-26 | Framework de orquestación (cadena vs grafo) | Arquitectura |
| Q-27 | Framework de interfaz y/o de API | Arquitectura |
| Q-28 | Estrategia y tamaño de chunking; solapamiento; `k` de recuperación | Arquitectura / Tuning |
| Q-29 | Biblioteca de validación tipada | Arquitectura |
| Q-30 | Estrategia de despliegue (local vs OCI Compute) | Arquitectura |
| Q-31 | Estructura de carpetas del repositorio | Arquitectura |

> El documento fuente **sugiere** opciones para Q-23 a Q-29 `(p.3, p.6)` pero declara explícitamente que no son vinculantes ("no hay exclusividad obligatoria", "también se aceptan soluciones y frameworks equivalentes", "Flexibilidad de Stack"). La única imposición tecnológica real del documento es **OCI Object Storage en capa Always Free**.

---

## 12. Risks

> Identificación, sin diseño de soluciones (esta fase no propone mitigaciones técnicas).

### 12.1 Riesgos funcionales

| ID | Riesgo | Impacto | Prob. | Deriva de |
|---|---|---|---|---|
| **R-01** | **4 de los 5 formatos pedagógicos no tienen estructura de salida definida.** Cada desarrollador inventará la suya y el contrato se fragmentará | 🔴 Alto | Alta | A-08 / Q-08 |
| **R-02** | **`anclaje_fuente_score` producido por el mismo LLM que redactó el contenido** = autoevaluación circular. El diferenciador central del producto queda como un número decorativo que no detecta alucinaciones | 🔴 Alto | Alta | A-10 / Q-10 |
| **R-03** | **Adaptación cosmética:** los paquetes de distintos perfiles difieren en adjetivos pero no en profundidad real. Falla AC-06.1 y AC-19.3, y con ellos la casilla 4 del Checklist —la que más visiblemente demuestra el valor del producto | 🔴 Alto | Media | H-04, R-01 |
| **R-04** | Cobertura parcial: se implementan sólo 2 perfiles y 2 formatos (mínimo del Checklist) mientras el documento define 4 y 5. Riesgo de percepción de producto incompleto ante el evaluador | 🟠 Medio | Media | H-17 |
| **R-05** | **El "gratis" del programa cubre OCI, no el LLM.** Un proveedor de pago introduce un costo que el documento no contempla y que contradice el espíritu declarado de gratuidad | 🔴 Alto | Media | NFR-COS-02 / Q-20 |
| **R-06** | **OCI en la ruta crítica durante la demostración en vivo.** Un fallo de red o de credenciales cuesta la demo completa aunque la generación funcione | 🟠 Medio-Alto | Media | A-12 / Q-14 |
| **R-07** | **Credenciales de OCI o de LLM versionadas en un repositorio GitHub público.** Riesgo de seguridad real y de incumplimiento del programa | 🔴 Alto | Media | NFR-SEC-01 |
| **R-08** | Agotamiento de los límites de la capa Always Free durante las pruebas iterativas | 🟡 Bajo-Medio | Baja | NFR-COS-01 |

### 12.2 Riesgos técnicos

| ID | Riesgo | Impacto | Prob. | Deriva de |
|---|---|---|---|---|
| **R-09** | **Demostración no reproducible** por la no-determinación del LLM: el escenario que funcionó en el ensayo produce otra cosa frente al jurado | 🟠 Medio | Alta | NFR-REL-04 / FR-GEN-10 |
| **R-10** | **Subestimar D11.** Sistema funcionando, entregado sin README con diagrama, sin 3 ejemplos y sin evidencia de 2×2: **se pierden 3 de 8 casillas (37,5%)** teniendo el producto listo. Es el modo de fallo más común en hackathons | 🔴 Alto | **Alta** | §8.1 |
| **R-11** | **Latencia acumulada** de la cadena (extracción + chunking + embeddings + n llamadas a LLM + carga a OCI) rompe la promesa de "minutos" y hace tediosa la demo en vivo | 🟠 Medio | Media | NFR-PRF-01, NFR-PRF-05 |
| **R-12** | **PDFs con layout complejo** (multicolumna, tablas, diagramas) producen texto degradado que contamina chunks, embeddings, generación y puntaje de fidelidad. El soporte multimodal —la red de seguridad natural— es opcional | 🟠 Medio-Alto | Alta | FR-ING-02, FR-ING-05 |
| **R-13** | **Dependencia de un único proveedor de LLM** sin plan alterno: si su cuota gratuita se agota o el servicio falla durante la evaluación, no hay ejecución que mostrar | 🟠 Medio | Media | NFR-SCA-02 |
| **R-14** | **Salida del LLM no parseable** rompe el requisito de tipado estricto de forma intermitente y difícil de reproducir | 🟠 Medio | Alta | FR-GEN-08, NFR-REL-02 |
| **R-15** | **Re-indexación redundante** en UC-03: los 3 escenarios re-procesan el mismo documento, triplicando costo de embeddings y latencia justo en el flujo de demostración | 🟡 Bajo-Medio | Media | A-02 / Q-06 |
| **R-16** | **Deriva de alcance hacia los diferenciales** (multi-agente, multimodal, quiz en vivo) antes de cerrar las 8 casillas obligatorias | 🟠 Medio | Media | §8.3 |

---

## DECISION GATE

### 1 · Qué quedó definido

- **Visión, actores y dominios funcionales**, con la distinción explícita entre el Autor de Contenido (quien opera) y el Estudiante (quien recibe, y que **no** es usuario del sistema en el MVP).
- **52 requisitos funcionales `MUST`**, más 13 `SHOULD`, 12 `COULD` y 4 `OUT OF SCOPE` con ID (más 5 exclusiones adicionales sin ID), cada uno etiquetado como explícito, inferencia o propuesta, con referencia de página.
- **20 User Stories** que cubren el 100% de los `MUST`, y **63 criterios de aceptación** verificables en formato Given/When/Then.
- **8 flujos end-to-end**, incluidos los caminos de error y los dos flujos opcionales.
- **MVP delimitado en 4 niveles**, con los diferenciales del documento mantenidos estrictamente fuera del alcance obligatorio.
- **Matriz de trazabilidad completa:** las 8 casillas del Checklist de Evaluación tienen FR, User Story y criterios de aceptación. **Cero casillas sin cobertura.**
- **Requisitos no funcionales** en las 9 categorías, sin inventar un solo valor numérico.
- Una única imposición tecnológica reconocida: **OCI Object Storage, capa Always Free**. Todo lo demás queda abierto.

### 2 · Qué quedó ambiguo

**16 ambigüedades** documentadas en §11.1. Las tres que más condicionan el diseño:

1. **A-08 — El documento exige 5 formatos pedagógicos y define la estructura de uno solo.** Es el vacío más grande de la fuente.
2. **A-10 — `anclaje_fuente_score` aparece en el contrato sin escala, sin método ni semántica**, siendo la anti-alucinación el valor central declarado del producto.
3. **A-01 — El contrato de entrada oficial recibe texto embebido, mientras el resto del documento exige ingestión de archivos.** El límite entre interfaz y núcleo no está definido.

Consecuencia medible: **3 criterios de aceptación (AC-08.4, AC-14.4, AC-17.3) no son verificables** hasta que se resuelvan Q-08, Q-14 y Q-12.

### 3 · Qué decisiones debemos tomar

**Bloqueantes — antes de tocar arquitectura** (§11.2):

| Orden | Decisión | Pregunta |
|---|---|---|
| 1º | Estructura de `items[]` para los 5 formatos, y cuántos se implementan | **Q-08** |
| 2º | Qué mide y cómo se calcula `anclaje_fuente_score` | **Q-10** |
| 3º | Umbral de fidelidad y acción correctiva | **Q-11** |
| 4º | Vías de entrada: archivo, texto, o ambas, y en qué superficie | **Q-01** |
| 5º | ¿OCI en la ruta crítica? Política ante fallo de carga | **Q-14** |
| 6º | ¿Interfaz, API, o ambas? | **Q-15** |
| 7º | Ciclo de vida del índice vectorial | **Q-06** |

**Además, una decisión de programa que no es técnica:** **Q-20 — quién asume el costo del LLM**, dado que la garantía "Always Free" del documento sólo cubre OCI.

### 4 · Qué información falta

| Falta | Impacto |
|---|---|
| Rúbrica de puntuación del Hackathon (si existe además del Checklist) | Sin ella, la priorización asume que las 8 casillas pesan igual |
| El documento técnico real que se usará en la demostración | Condiciona R-12 (calidad de extracción) y los 3 escenarios |
| Límites concretos de la capa Always Free aplicables al equipo | Condiciona NFR-COS-01, NFR-SCA-01 y R-08 |
| Fecha de entrega y horas-persona disponibles | Sin esto, §8.2 (`SHOULD`) no es priorizable de verdad |
| Composición del equipo y reparto de dominios | Condiciona FR-DOC-01 (commits colaborativos) |
| Formato y duración de la presentación final | Condiciona R-09 y R-11 |
| Ejemplos de salida esperada para los 4 formatos no documentados | Si el organizador los tiene, resuelve Q-08 sin inventar |

### 5 · Qué NO debemos decidir todavía

Registrado en §11.5 y **deliberadamente no resuelto en este documento**:

- Proveedor y modelo de LLM · modelo de embeddings · Vector Store
- Framework de orquestación, y si es cadena o grafo
- Framework de interfaz y/o de API
- Biblioteca de validación tipada
- Estrategia y tamaño de chunking, solapamiento, `k` de recuperación
- Estructura de carpetas, empaquetado y estrategia de despliegue
- Diseño de los prompts
- Si se despliega en OCI Compute

El documento fuente **sugiere** opciones para casi todas y declara explícitamente que **ninguna es obligatoria**. Convertir una sugerencia en decisión antes de la fase de arquitectura es cerrar opciones sin haber evaluado nada.

---

### ⏸ Estado: ESPERANDO APROBACIÓN

**No se avanza a la fase de arquitectura.**

Para desbloquear la siguiente fase se necesita:

1. **Aprobación o corrección** de la definición funcional (§1 a §10).
2. **Respuesta a las 7 preguntas bloqueantes** de §11.2 — en especial **Q-08**, que define el contrato de salida completo.
3. **Decisión sobre Q-20** (costo del LLM), que es condición del programa, no de diseño.

Con eso resuelto, la fase 2 puede producir la arquitectura y la selección tecnológica sobre una base verificable.
