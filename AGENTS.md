# AGENTS.md — NuevaMente

Guía operativa para agentes que trabajan en este repo. Complementa a `CLAUDE.md`, no lo reemplaza.
Todo el texto, comentarios y docstrings van **en español**.

## Qué es y material de prueba

NuevaMente adapta documentación técnica densa (PDF/MD/txt) a paquetes educativos por perfil y
formato, con **fidelidad verificable a la fuente** (`anclaje_fuente_score`).

Para el MVP el equipo simula una empresa de capacitación en certificaciones ágiles, así que el
material de prueba son **guías oficiales de certificación** (Scrum Fundamentals, Scrum Master,
Product Owner, AI Agile, Enterprise Agile Coach). Chunking, prompts y perfiles se validan contra
ese tipo de material, no contra texto genérico.

## Fuentes de verdad

- **Oficial y vigente — bóveda Obsidian** (fuera del repo):
  `C:\Users\marely\OneDrive\Documentos\Obsidian\Mi_bóveda\02_Proyectos\NuevaMente\`
  Archivos clave: `AGENTS.md`, `MEMORY-NUEVAMENTE.md`, `Docs/Spec de construcción por agente.md`,
  `Docs/agent supervisor.md`, `Docs/Unidad Estrategica — Víctor y Obed.md`.
- **`CLAUDE.md`**: válido para el **contrato congelado** y convenciones de trabajo. Quedó
  desactualizado en equipo, stack y arquitectura (es del 18-sep; el equipo se reorganizó después).
  Lo revisa Franklin. Ante choque, manda la spec de la bóveda.
- El código real manda sobre cualquier prosa.

## Comandos

```bash
python verificar_entorno.py                                  # qué falta en TU máquina
pytest tests/ -q                                             # toda la suite
python -m pytest tests/test_contratos.py::test_ejemplo_oficial_valida
python src/config.py                                         # valida configuración
python src/llm_provider.py                                   # prueba construir proveedores
python src/servidor_objeStorageOracle.py --test              # E2E contra OCI (requiere credenciales)
python src/Cliente_agemte.py                                 # prueba conexión MCP
```

## Estructura: qué existe y qué no

Existe hoy: `src/contracts/` (congelado), `src/config.py`, `src/errores.py`,
`src/llm_provider.py`, y el par MCP `src/servidor_objeStorageOracle.py` + `src/Cliente_agemte.py`.

**Todavía no existe** (está planificado en la bóveda): `app.py`, `src/ingesta/`, `src/rag/`,
`src/pedagogia/`, `src/orquestacion/`, `src/persistencia/`, `notebooks/`, `ejemplos/`.
`src/agentes/` existe solo en la rama `origin/feature/sergio-redactor-pedagogico`.

## Gotchas (cosas que un agente falla si no las sabe)

- **Imports partidos.** `src/config.py`, `src/llm_provider.py` y `src/errores.py` importan entre
  sí por nombre pelado (`from config import settings`), así que necesitan `src/` en `sys.path`
  (correr como script, o agregar `src/`). En cambio `tests/` inserta la raíz del repo e importa
  `from src.contracts import ...`. Consecuencia: `python src/llm_provider.py` funciona, pero
  `python -m src.llm_provider` **no**.
- **`requirements.txt` está incompleto** frente a `verificar_entorno.py`: no incluye `pytest` ni
  las integraciones `langchain-ollama`, `langchain-google-genai`, `langchain-anthropic`.
- **`.env` nunca se versiona** (riesgo R-07). Ya está en `.gitignore`.
- **Un campo o clave mal escrito no siempre tira error**: en Pydantic `extra="forbid"` lo salva,
  pero una clave mal escrita del `AgentState` deja el estado vacío en silencio.

## El contrato (`src/contracts/`) — congelado

- No editar `tests/test_contratos.py::test_ejemplo_oficial_valida` para que pase: **arreglá el código**.
- `extra="forbid"` en todos los modelos.
- Forma canónica **corta** (`"Principiante"`, `"Flashcards"`); la forma larga es alias de entrada.
- Claves JSON **sin tildes** (`documento_titulo`, `pista_didactica`).
- Los `items[]` validan contra el esquema de SU formato. `respuesta_correcta` del Quiz debe
  existir entre los `id` de `opciones`.
- `status` no puede mentir: si falla OCI o la fidelidad quedó baja → `exito_con_advertencias`.

## Arquitectura vigente (spec de la bóveda, 25-sep)

- **5 agentes en `src/agentes/`**: `supervisor` (clasifica intención), `investigador` (verifica
  cobertura en Chroma), `redactor_pedagogico`, `critico_revisor`, `modificador`.
- **Nodos determinísticos** (no agentes): `buscador_documentos`, `ingesta`, `guardado_final`.
- **Acceso a OCI no agéntico**: solo esos nodos determinísticos tocan OCI, vía `Cliente_agemte.py`.
  Ningún agente accede a OCI directo.
- **Grafo**: `grafo.py` con stubs + `agent_state.py` (State como `TypedDict`). Contadores
  `intentos_redactor` / `vueltas_modificacion` **se incrementan, nunca se resetean**.
- **Interrupts HITL**: `confirmar_ejecucion`, `confirmar_modificacion` (y aclaración pendiente).
- **Supervisor**: router por reglas (no LLM evaluador) para el routing; el agente supervisor
  solo clasifica intención.
- **`anclaje_fuente_score`**: por **similitud coseno** de embeddings, no una segunda llamada al LLM.
  El crítico/revisor solo aporta la observación cualitativa.
- **Patrón de agente (el de Sergio)**: núcleo puro `async` que recibe sus dependencias
  **inyectadas** (un `generador` con `async generate(*, prompt, output_model)`), prompt en
  `src/prompts/`, tests con dobles (`FakeGenerator`). No instanciar el cliente LLM dentro del agente.
- ⚠ Nombres de archivo, de función de nodo y claves del `AgentState` deben coincidir con lo que
  importa `grafo.py`. Confirmar antes de fijarlos.

## OCI Object Storage (requisito obligatorio del Hackathon)

- Se implementa por **servidor MCP** `src/servidor_objeStorageOracle.py` (stdio) + cliente
  `src/Cliente_agemte.py`. **No** existe `src/persistencia/oci_storage.py`.
- Prefijos del bucket: `fuentes/` (documentos de entrada), `generados/`, `generados/formateados/`.
- Auth: Instance Principal en la VM; en local `OCI_LOCAL_DEV=1` para saltear el timeout y usar
  `~/.oci/config`.
- `Cliente_agemte.py` lanza el servidor por nombre relativo → correr con **cwd = `src/`**.
- El servidor lee `OCI_BUCKET_NAME` directo del entorno (default `nuevamente-storage`),
  **no** pasa por `src/config.py`.

## Equipo y ramas

- **Ruta crítica del MVP:** Franklin (integración), Oscar (RAG), Sergio (pedagogía),
  Marely (orquestación/supervisor/verificador).
- **Unidad estratégica:** Víctor y Obed — adiciones diferenciales **fuera de la ruta crítica**;
  su resultado se ve en la demo final, no en el flujo principal.
- **Ignacio:** PM (sin rama técnica).
- Ramas personales: `feature/frank-avances`, `feature/marely-orquestacion`,
  `feature/sergio-redactor-pedagogico`, `feature/oscar-rag`, `feature/victor-calidad`,
  `feature/obed-ui`.

## Git

- Rama personal → push a esa rama remota → **PR a `dev`**. Los merges a `main` salen de `dev`.
- **Nunca** commitear directo a `main` ni a `dev`. Nunca `--force` sobre ellas.
- Convención de ramas: `feature/<nombre>-<tema>`, `fix/<tema>`, `docs/<tema>`.
- **Conventional Commits** (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`), en imperativo.
- `.env` nunca se versiona.
