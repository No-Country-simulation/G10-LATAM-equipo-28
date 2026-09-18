# NuevaMente — Hoja de arranque del equipo

**Fecha:** 18 de septiembre de 2026 · **Entrega:** 9 de octubre · **Equipo:** 3 personas comprometidas

> Esta hoja responde tres preguntas concretas y reúne en un solo lugar lo que estaba repartido entre los documentos 02, 03 y 04. Es la única que hace falta tener abierta para empezar.

---

## Respuesta corta a las tres preguntas

| Pregunta | Respuesta | Dónde estaba |
|---|---|---|
| **¿Definimos los prerrequisitos?** | Estaban implícitos y repartidos. **Ahora son una lista explícita** (§1) y un script que los verifica en tu máquina (`verificar_entorno.py`) | Nuevo, en esta hoja |
| **¿Definimos la arquitectura?** | **Sí, las 9 decisiones están cerradas** (§2) | Documento 04, §1 |
| **¿Está clara la estructura de carpetas?** | **Sí, y ya existe en disco** — `src/contracts/` está construido y probado (§3) | Documento 04, §2 |
| **¿Cuáles son los roles para 3 personas?** | Tres roles con **dueño de archivos definido** (§4) | Nuevo, concretado aquí |

---

## 1. Prerrequisitos

### 1.1 · Lo que cada persona instala en SU máquina

| # | Qué | Cómo | Por qué |
|---|---|---|---|
| 1 | **Python 3.11 o superior** | python.org o pyenv | Base de todo |
| 2 | **Entorno virtual** | `python -m venv .venv` y activarlo | Evita que las versiones de uno rompan las del otro |
| 3 | **Dependencias** | `pip install -r requirements.txt` | Ya está el archivo |
| 4 | **Ollama** + modelo de embeddings | ollama.com/download, luego `ollama pull nomic-embed-text` | Es lo que evita gastar la cuota gratuita de Gemini vectorizando chunks |
| 5 | **Clave propia de Gemini** | aistudio.google.com/apikey | **Cada quien la suya.** Si comparten una, comparten la cuota gratuita y se agota tres veces más rápido |
| 6 | **Credenciales de OCI** | Consola OCI → Perfil → API keys → Add API key → guardar en `~/.oci/config` | Requisito obligatorio del Hackathon |
| 7 | **Git configurado** | `git config --global user.name "..."` | Casilla 8: commits claros y colaborativos |
| 8 | **`.env` propio** | `cp .env.example .env` y llenar las claves | ⛔ Nunca se sube al repo |

**Para verificar todo de una vez:**

```bash
python verificar_entorno.py
```

Dice exactamente qué te falta y cómo arreglarlo. Si los tres lo corren y sale verde, arrancan parejos y nadie pierde medio día el 22 descubriendo que le faltaba un paquete.

### 1.2 · Lo que el equipo hace UNA vez

| # | Qué | Quién | Cuándo | Bloquea |
|---|---|---|---|---|
| 1 | Crear el repo en GitHub **con el `.gitignore` en el primer commit** | Rol 3 | 19 sept | Todo |
| 2 | Crear el bucket de OCI **en la home region** | Rol 3 | 19 sept | 🔴 Casilla 6, sin sustituto |
| 3 | Subir un archivo a mano al bucket, para confirmar que funciona | Rol 3 | 19 sept | 🔴 Casilla 6 |
| 4 | Compartir las credenciales de OCI con el equipo | — | 19 sept | Que no dependa de una persona |
| 5 | Preguntar a los organizadores si hay ejemplos de salida para los formatos no documentados | Cualquiera | 19 sept | Nada, pero ahorraría trabajo |
| 6 | Conseguir los documentos técnicos de prueba | Cualquiera | 23 sept | Ajustar el chunking |

> **El `.gitignore` va en el primer commit, no después.** Una clave subida a GitHub no se borra con `git rm`: queda en el historial y hay que rotarla. Es el riesgo R-07.

---

## 2. Arquitectura — las 9 decisiones, cerradas

| Pieza | Decisión |
|---|---|
| LLM redactor | **Gemini** (capa gratuita); respaldo por `.env`, sin tocar código |
| Embeddings | **Ollama local** (`nomic-embed-text`) |
| Vector store | **ChromaDB**, persistente, una colección por `document_id` |
| Orquestación | **LangGraph** — con repliegue a cadena lineal si el 25 de septiembre no corre |
| Interfaz | **Streamlit** (no se construye API REST) |
| Validación | **Pydantic v2** — ✅ ya construido y probado |
| Chunking | 1000 / solapamiento 150 / `k=5` — se ajusta con los documentos reales del 23 |
| Despliegue | Local. OCI Compute sólo si sobra margen después del 5 de octubre |
| Estructura | §3 de esta hoja |

El detalle y la justificación de cada una están en el documento 04, §1.

---

## 3. Estructura de carpetas

**Lo que ya existe en disco** (construido y con 38 pruebas en verde):

```
nuevamente/
├── .gitignore              ✅  protege el .env
├── .env.example            ✅  plantilla de configuracion
├── requirements.txt        ✅
├── verificar_entorno.py    ✅  cada quien lo corre en su maquina
├── src/
│   ├── config.py           ✅  toda la configuracion entra por aqui
│   ├── llm_provider.py     ✅  UNICO archivo que nombra proveedores
│   ├── errores.py          ✅  catalogo de codigos + contrato de error
│   └── contracts/          ✅  LA FRONTERA — se congela el 22 sept
│       ├── enums.py            perfiles, formatos, nichos, estados
│       ├── formatos.py         los 5 esquemas de items[]
│       ├── request.py          contrato de entrada
│       └── response.py         contrato de salida
└── tests/
    └── test_contratos.py   ✅  38 pruebas
```

**Lo que falta construir**, con su dueño:

```
nuevamente/
├── app.py                  ← Rol 3   Streamlit
├── src/
│   ├── ingesta/            ← Rol 1
│   │   ├── extractor.py        PDF · Markdown · texto
│   │   └── normalizador.py
│   ├── rag/                ← Rol 1
│   │   ├── chunker.py
│   │   ├── indexador.py        Chroma, cache por document_id
│   │   └── recuperador.py
│   ├── pedagogia/          ← Marely   (funcion pura, sin dependencias)
│   │   ├── bloom.py · andamiaje.py · registro.py · foco.py
│   │   └── mapping.py
│   ├── orquestacion/       ← Rol 2
│   │   ├── estado.py · grafo.py
│   │   └── nodo_planificador.py · nodo_redactor.py · nodo_verificador.py
│   ├── prompts/            ← Rol 2
│   └── persistencia/       ← Rol 3
│       └── oci_storage.py
├── notebooks/              ← Rol 1   notebook de la pipeline (casilla 8)
├── ejemplos/               ← compartido   los 3+ ejemplos (casilla 7)
└── docs/                   ← Rol 3   README, diagrama, arquitectura
```

**La regla que evita choques:** cada carpeta tiene **un solo dueño**. Si necesitás tocar la carpeta de otro, se habla antes. Lo único compartido es `src/contracts/`, y por eso se congela.

---

## 4. Los tres roles

### Rol 1 · Pipeline de datos

**Dueño de:** `src/ingesta/`, `src/rag/`, `notebooks/`

| Trabajo | Horas |
|---|---|
| Extractores de PDF, Markdown y texto + normalización + validación de entrada | 6 |
| Chunking, embeddings, Chroma, recuperación, caché por documento | 8 |
| Notebook que evidencia la pipeline (lo pide la p.3 del documento) | 5 |
| **Total propio** | **19** |

**Perfil que encaja:** quien esté más cómodo con Python de datos y manejo de archivos.
**Ventaja:** es el carril más independiente. Se prueba contra los contratos, sin esperar a nadie.

### Rol 2 · Inteligencia

**Dueño de:** `src/orquestacion/`, `src/prompts/`

| Trabajo | Horas |
|---|---|
| Grafo LangGraph: estado, nodos, aristas condicionales | 10 |
| Prompts por formato (4 formatos, con few-shot y role prompting) | 14 |
| Verificador de fidelidad + umbral 0.80 + lazo de reintento | 12 |
| Campo `anclaje` por ítem | 2 |
| **Total propio** | **38** |

**Perfil que encaja:** **Franklin** — propuso el flujo de agentes, tiene el interés.
**Es el carril más pesado y el más riesgoso.** Por eso el trabajo compartido se le carga menos.

### Rol 3 · Producto y entrega

**Dueño de:** `app.py`, `src/persistencia/`, `docs/`, `README.md`

| Trabajo | Horas |
|---|---|
| Interfaz Streamlit: carga, parámetros, render del paquete | 10 |
| OCI Object Storage: subida de los dos artefactos + degradación controlada | 8 |
| Manejo de errores de punta a punta, con mensajes amigables | 4 |
| README con arquitectura, diagrama y guía de instalación (casilla 8) | 11 |
| **Total propio** | **33** |

**Perfil que encaja:** quien pueda sostener documentación además de código — es lo primero que se abandona bajo presión, y son 3 de las 8 casillas.
**Arranca primero:** el bucket de OCI y el repo son suyos, y bloquean a los demás.

### Módulo de pedagogía · Marely

**Dueña de:** `src/pedagogia/` — **8 h**

Va aparte porque es suyo y porque es el único trabajo que **puede empezar hoy mismo**: es una función pura, sin dependencias del grafo ni de los contratos.

```
build_pedagogical_spec(perfil: PerfilDestinatario, nivel_detalle: NivelDetalle) -> PedagogicalSpec
build_pedagogical_prompt_fragment(spec: PedagogicalSpec) -> str
```

Con las tres correcciones del documento 03: función pura, `nivel_detalle` como texto del enum, y el cuarto eje `foco`.

### Trabajo compartido — 28 h

| Trabajo | Horas | Cómo se reparte |
|---|---|---|
| Integración y corrección de fallas | 15 | Los tres, según dónde caiga |
| Los 3+ ejemplos de ejecución (casilla 7) | 5 | Uno cada quien, con su propio escenario |
| Pitch: guion, 2 ensayos, grabación de respaldo | 8 | Los tres — todos presentan |

### Cómo queda la carga

| Persona | Propio | + compartido | Total | Capacidad (63 h) |
|---|---|---|---|---|
| Rol 1 | 19 | 11 | **30 h** | holgado |
| Rol 2 (Franklin) | 38 | 7 | **45 h** | ajustado |
| Rol 3 | 33 | 10 | **43 h** | ajustado |
| Marely (pedagogía + uno de los roles) | 8 | — | **+8 h** | — |

**Total: 126 h contra 189 h de capacidad.** El margen de ~60 h es la reserva del proyecto, no tiempo libre.

> **Marely toma pedagogía MÁS uno de los tres roles.** Lo natural es el Rol 1, porque ambos son módulos independientes que se prueban solos, y quedaría en 38 h. Pero eso lo deciden ustedes.

---

## 5. Qué hace cada quien el lunes

**Rol 3 — primero, porque desbloquea a los otros dos**

1. Crear el repo con el `.gitignore` en el primer commit.
2. Subir `src/contracts/`, `tests/`, `requirements.txt`, `.env.example`, `verificar_entorno.py`.
3. Crear el bucket de OCI en la home region y subir un archivo a mano.

**Rol 1 y Rol 2 — en paralelo**

1. Clonar, `python verificar_entorno.py`, arreglar lo que salga rojo.
2. Leer `src/contracts/` completo. Es contra eso que van a programar.
3. Empezar por sus carpetas.

**Marely**

Puede arrancar `src/pedagogia/` sin esperar el repo: es una función pura. Sólo necesita los enums `PerfilDestinatario` y `NivelDetalle`, que ya existen.

---

## 6. Las tres fechas que importan

| Fecha | Qué | Si no se cumple |
|---|---|---|
| **22 sept** | Contratos congelados + un archivo visible en el bucket de OCI | 🔴 Se detiene todo hasta resolver OCI: es la única casilla sin sustituto |
| **25 sept** | El grafo de LangGraph corre de punta a punta | 🔻 Se colapsa a cadena lineal (~4 h). Se decide ese día, no en octubre |
| **5 oct** | **Congelamiento de código** | Lo que no funcione ese día no entra. Del 6 al 9: sólo documentación, ejemplos y pitch |
