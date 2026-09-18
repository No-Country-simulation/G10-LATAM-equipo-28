# CLAUDE.md — NuevaMente

Memoria de proyecto. Claude Code lee este archivo al arrancar cada sesión en esta carpeta
y en cualquier subcarpeta.

**Contesta en español.** Términos técnicos (chunking, embeddings, prompt, commit) en inglés.

---

## 1. Qué es esto

**NuevaMente** — Hackathon ONE G10 (Oracle Next Education & Alura), equipo LATAM 28.

Ingiere documentación técnica densa (PDF, Markdown, texto) y la transforma en **paquetes
educativos personalizados**, parametrizados por perfil del destinatario, formato pedagógico
y nicho, usando RAG para **anclar cada afirmación en el material original**.

El diferenciador **no** es "generar contenido con IA" —eso es commodity— sino **generar
contenido con fidelidad verificable a una fuente**. Toda decisión de diseño se juzga contra eso.

| Dato | Valor |
|---|---|
| Entrega | **9 de octubre de 2026** |
| Equipo | 3 personas comprometidas (Oscar, Marely, Franklin) + 1 que no entra al camino crítico |
| Capacidad | ~189 h · Alcance ~127 h · Margen ~60 h, que es **reserva, no tiempo libre** |
| Presentación | Elevator pitch de **5 minutos** → demo en vivo de 90-120 segundos |

---

## 2. Cómo se evalúa — las 8 casillas

Esto es lo único que decide la nota. No hay rúbrica adicional: **las 8 pesan igual.**

1. Ingestión funcional de documentos técnicos (PDF, Markdown, texto)
2. RAG con chunking, embeddings y búsqueda vectorial en Vector Store
3. Orquestación con LLM
4. Adaptar el mismo contenido a **≥2 perfiles** y **≥2 formatos**
5. Salida JSON estructurada **e** interfaz interactiva **o** API REST
6. **Integración activa con OCI Object Storage (Always Free)** ← la única sin sustituto
7. **≥3 ejemplos de ejecución** documentados
8. **Documentación en GitHub con diagrama de arquitectura**

> **Las casillas 4, 7 y 8 no son código.** Son el 37,5% de la nota y son lo primero que se
> abandona bajo presión. Es el riesgo N.º 1 del proyecto (R-10). Nunca se sacrifican.

---

## 3. Decisiones cerradas — NO reabrir

Cerradas en el Decision Gate (`docs/02_Decision-gate_v2_RESUELTO.md`). Si algo aquí parece
mejorable, **decilo, no lo cambies por tu cuenta**.

| ID | Decisión |
|---|---|
| **D-01** | **4 de 5 formatos** en el MVP: Flashcards, Tutorial, Resumen Ejecutivo, Quiz. Guion de Clase queda declarado en el contrato y devuelve `FORMATO_NO_DISPONIBLE_EN_MVP` |
| **D-02** | `anclaje_fuente_score` lo calcula un **agente verificador SEPARADO**: segunda llamada al LLM, rol distinto, que recibe sólo las afirmaciones + los chunks. Score = soportadas ÷ totales, escala 0.0-1.0, las parciales cuentan 0.5. **Nunca autoevaluación del redactor** — eso es circular y no detecta nada |
| **D-03** | Umbral **0.80**. Bajo el umbral → regenerar **UNA vez** con más contexto → si sigue bajo, entregar marcado como `"Requiere revision"`. Máximo 1 reintento: hay 90 segundos de demo |
| **D-04** | La acción principal acepta **dos modos**: archivo (PDF/MD/txt) o texto embebido (`documento_titulo` + `documento_contenido`, el contrato oficial de la p.4). Convergen internamente |
| **D-05** | **Degradación controlada:** si falla la carga a OCI, el paquete se entrega igual con `status="exito_con_advertencias"` y `status_upload="fallido"`. Una caída de red no puede costar la demo |
| **D-06** | **Sólo interfaz** (Streamlit). No se construye API REST. El checklist dice "interfaz **o** API" |
| **D-07** | Índice vectorial **persistente por `document_id`**. Se indexa una vez y se reutiliza: la demo genera 4 paquetes del mismo documento |
| **D-08** | LLM en capas gratuitas; si se agotan, el costo lo asume el equipo. **Exige proveedor de respaldo configurado desde el día 1** |

**Además:** cada ítem generado lleva un campo `anclaje` con los IDs de los chunks que lo
sustentan. Le da trabajo hecho al verificador y permite señalar en pantalla de dónde salió
cada dato — el mejor momento del pitch.

---

## 4. Stack — decidido, no reabrir

| Pieza | Elección | Por qué |
|---|---|---|
| LLM redactor | **Gemini** (capa gratuita) | Referencia del curso; respaldo por `.env` |
| Embeddings | **Ollama local** (`nomic-embed-text`) | Una llamada POR CHUNK: local es gratis, ilimitado y sin red |
| Vector store | **ChromaDB**, una colección por `document_id` | Implementa D-07 |
| Orquestación | **LangGraph** | El reintento de D-03 es una arista condicional; los nodos son los agentes |
| Interfaz | **Streamlit** | Carga de archivos incorporada |
| Validación | **Pydantic v2** | Cubre el tipado estricto que exige el documento |
| Chunking | 1000 / overlap 150 / `k=5` | Punto de partida; se ajusta con documentos reales |

> **🔻 Repliegue (25 sept):** si el grafo de LangGraph no corre de punta a punta, se colapsa
> a cadena lineal de LangChain (~4 h). Las tres responsabilidades —planificar, redactar,
> revisar— no cambian; cambia el cableado.

---

## 5. El contrato — la frontera del sistema

`src/contracts/` es lo que permite que tres personas trabajen en paralelo sin pisarse.
**Está congelado.** Cambiarlo obliga a coordinar a los tres, así que se cambia sólo con
acuerdo explícito del equipo.

```
src/contracts/
├── enums.py       perfiles · formatos · nichos · nivel de detalle · estados
├── formatos.py    los 5 esquemas de contenido_adaptado.items[]
├── request.py     SolicitudAdaptacion
└── response.py    PaqueteEducativo
src/errores.py     catalogo de codigos + contrato de error + excepciones
```

### Reglas del contrato

- **Claves JSON sin tildes.** El documento oficial usa `documento_titulo`,
  `introduccion_contextualizada`, `pista_didactica`. Se respeta.
- **Forma canónica corta:** `"Principiante"`, `"Flashcards"` — es la que aparece en el
  ejemplo oficial, y la salida debe coincidir carácter por carácter con él. La forma larga
  (`"Principiante / Transición de Carrera"`) se acepta como alias en la entrada; la
  comparación ignora tildes, mayúsculas y puntuación.
- **`extra="forbid"` en todos los modelos.** Un campo mal escrito es un error, no se ignora.
- **Los `items[]` validan contra el esquema de SU formato**, no contra "alguno".
- **`respuesta_correcta` del Quiz debe existir entre los `id` de `opciones`.** Es el error
  más común de un LLM generando quizzes: se valida en el esquema, no se confía en el modelo.
- **El `status` no puede mentir:** si la carga a OCI falló o la fidelidad quedó bajo el
  umbral, `status` **no** puede ser `"exito"`.

### La prueba que manda

`tests/test_contratos.py::test_ejemplo_oficial_valida` toma el Ejemplo de Solicitud y el de
Respuesta **tal como están en el documento del Hackathon** y los valida sin modificarlos.
**Si esa prueba se rompe, nos apartamos de la especificación oficial.** No la ajustes para
que pase: arreglá el código.

```bash
pytest tests/ -q          # 38 pruebas, deben estar todas en verde
```

---

## 6. Estructura y dueños

Cada carpeta tiene **un solo dueño**. Si hay que tocar la de otro, se habla antes.

```
.
├── CLAUDE.md               este archivo
├── .env.example            plantilla (el .env real NUNCA se versiona)
├── .gitignore
├── requirements.txt
├── verificar_entorno.py    cada quien lo corre en su maquina
├── app.py                  ← Rol 3   Streamlit             [PENDIENTE]
├── src/
│   ├── config.py           ✅ toda la configuracion entra por aqui
│   ├── llm_provider.py     ✅ UNICO archivo que nombra proveedores
│   ├── errores.py          ✅
│   ├── contracts/          ✅ CONGELADO
│   ├── ingesta/            ← Rol 1   PDF · MD · txt         [PENDIENTE]
│   ├── rag/                ← Rol 1   chunker · indexador · recuperador  [PENDIENTE]
│   ├── pedagogia/          ← Marely  funcion pura           [PENDIENTE]
│   ├── orquestacion/       ← Rol 2   grafo + nodos          [PENDIENTE]
│   ├── prompts/            ← Rol 2                          [PENDIENTE]
│   └── persistencia/       ← Rol 3   oci_storage.py         [PENDIENTE]
├── notebooks/              ← Rol 1   casilla 8              [PENDIENTE]
├── ejemplos/               ← compartido  casilla 7          [PENDIENTE]
├── tests/                  ✅ test_contratos.py
└── docs/                   especificacion y decisiones
```

**Roles:** Rol 1 = pipeline de datos (ingesta + RAG). Rol 2 = inteligencia (grafo, prompts,
verificador) — **el más pesado**, Franklin. Rol 3 = producto y entrega (Streamlit, OCI,
README) — **arranca primero**, porque el repo y el bucket bloquean a los demás.
Marely lleva `src/pedagogia/` además de su rol.

---

## 7. Módulo de pedagogía

Propuesta de Marely, adoptada. Ataca el riesgo de que la adaptación entre perfiles sea
cosmética: traduce el perfil a **parámetros concretos y verificables** que el redactor consume.

```python
build_pedagogical_spec(perfil: PerfilDestinatario, nivel_detalle: NivelDetalle) -> PedagogicalSpec
build_pedagogical_prompt_fragment(spec: PedagogicalSpec) -> str
```

| Perfil | Bloom's | Andamiaje | Registro | Foco |
|---|---|---|---|---|
| Principiante | Entender (2) | Alto | Cotidiano | Comprensión conceptual |
| Desarrollador | Aplicar (3) | Medio | Técnico | Ejecución práctica |
| Lider Tecnico | Evaluar (5) | Bajo | Técnico-estratégico | Criterio de decisión |
| Gestor Ejecutivo | Entender (2) | Alto | Ejecutivo | Impacto en negocio |

**Es función pura**, sin dependencias del grafo ni del state. Se puede construir y probar sola.

---

## 8. Reglas de trabajo

### Seguridad — riesgo R-07

- **El `.env` nunca se versiona.** El `.gitignore` lo cubre y va en el primer commit.
- Tampoco: `*.pem`, `~/.oci/`, `oci_api_key*`.
- Antes de entregar: `git log --all --full-history -- .env` debe salir **vacío**.
- Una clave subida no se borra con `git rm`: queda en el historial. Hay que **rotarla**.
- Los mensajes de error al usuario **nunca** llevan trazas, rutas ni nombres internos.

### Código

- Validar entrada **antes** de llamar al LLM. Una solicitud inválida no puede consumir cuota.
- Nada se sube a OCI antes de pasar la validación de salida.
- Los prompts viven en `src/prompts/`, no incrustados en la lógica.
- Ningún archivo nombra un proveedor de LLM salvo `src/llm_provider.py`.
- Comentarios y docstrings en español.

### Git

- Commits claros y en español. La casilla 8 evalúa "commits claros y colaborativos".
- Los tres deben tener commits propios: que uno solo suba todo se nota y resta.

---

## 9. Fechas que no se mueven

| Fecha | Qué | Si no se cumple |
|---|---|---|
| **22 sept** | Contratos congelados + un archivo visible en el bucket de OCI | 🔴 Se detiene todo: casilla 6 no tiene sustituto |
| **23 sept** | Llegan los documentos reales → ajustar chunking **con ellos** | — |
| **25 sept** | El grafo corre de punta a punta | 🔻 Se colapsa a cadena lineal |
| **30 sept** | Rebanada vertical completa con 2 formatos | Se recorta alcance |
| **5 oct** | **CONGELAMIENTO DE CÓDIGO** | Lo que no funcione ese día no entra. Del 6 al 9: sólo docs, ejemplos y pitch |
| **7 oct** | **Grabar la demo en video** | 2 h que eliminan el riesgo de que la red arruine el pitch |
| **9 oct** | Entrega | — |

**Orden de recorte si falta tiempo:** cae el Quiz → cae el Resumen Ejecutivo → **nunca** cae
la documentación.

---

## 10. Riesgos vivos

| ID | Riesgo | Estado |
|---|---|---|
| **R-10** | Subestimar documentación: 3 de 8 casillas se pierden con el sistema funcionando | 🔴 **El N.º 1** |
| **R-13** | Se agota la cuota gratuita del LLM en plena semana final | 🔴 Exige proveedor de respaldo ya configurado |
| **R-03** | Adaptación cosmética entre perfiles | 🟡 Mitigado por el módulo de pedagogía |
| **R-12** | PDFs con tablas o multicolumna producen texto degradado | 🟡 Se sabrá el 23 con los documentos reales |
| **R-09** | Demo no reproducible por no determinismo del LLM | 🟡 Temperatura baja + video de respaldo |

---

## 11. Documentos de referencia

En `docs/`, en orden de utilidad para trabajar:

| Archivo | Qué contiene |
|---|---|
| `05_Arranque-del-equipo.md` | Prerrequisitos, roles, qué hace cada quien el lunes |
| `04_Arquitectura-y-plan-de-trabajo.md` | Las 9 decisiones técnicas, el diagrama Mermaid, el plan de 21 días |
| `02_Decision-gate_v2_RESUELTO.md` | Las 8 decisiones D-01 a D-08 y los esquemas JSON de los 5 formatos |
| `03_Propuesta-Marelys_y_config-LLM.md` | El módulo de pedagogía y cómo funciona el intercambio de proveedores |
| `nuevamente-especificacion-funcional.md` | La especificación completa: 52 requisitos MUST, 20 user stories, 63 criterios de aceptación, matriz de trazabilidad |

**Todo lo que se afirma sobre el Hackathon está etiquetado** `[EXP]` (explícito en el
documento oficial, con página), `[INF]` (inferencia necesaria) o `[PROP]` (propuesta). Si
necesitás justificar algo ante el equipo, la etiqueta dice de dónde salió.

---

## 12. Antes de escribir código

```bash
python verificar_entorno.py     # dice qué te falta en TU máquina
pytest tests/ -q                # 38 en verde
```

Y leé `src/contracts/` completo. Es contra eso que se programa.
