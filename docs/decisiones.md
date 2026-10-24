# Decisiones de arquitectura — NuevaMente

> **Qué es este documento.** Índice de las decisiones que dan forma al sistema: qué se decidió,
> **dónde está implementado** y en qué estado quedó. No reemplaza a
> [`02_Decision-gate_v2_RESUELTO.md`](02_Decision-gate_v2_RESUELTO.md) —ese documento explica el
> razonamiento completo de D-01 a D-08—: acá se agrega lo que ese documento no tiene, que es el
> **estado real en el código**.
>
> **Referencia:** `main` @ `346f631` (tag `v1.0.1`). Fecha: 2026-10-24.

## 1. Decisiones del Decision Gate

| ID | Decisión | Estado | Dónde vive |
|---|---|---|---|
| **D-01** | Se implementan **4 de los 5** formatos pedagógicos. El Guion de Clase queda declarado en el contrato y se rechaza con `FORMATO_NO_DISPONIBLE_EN_MVP` | ✅ Cumplida | `src/contracts/enums.py:145`, `request.py:102`, `formatos.py:176` |
| **D-02** | `anclaje_fuente_score` lo calcula un **verificador separado**, no el redactor | ✅ Cumplida (vía LLM) | `src/agentes/agente_critico_revisor.py:7`, `src/llm_provider.py:171`, `src/config.py:101` |
| **D-03** | Umbral **0.80**, **un** reintento, luego entregar marcado como *Requiere revisión* | ✅ Cumplida | `src/config.py:121-124`, `src/agentes/agente_critico_revisor.py:109`, `src/contracts/response.py:107` |
| **D-04** | La acción principal acepta **dos vías**: archivo (PDF/MD/TXT) y texto embebido | ✅ Cumplida | `src/contracts/request.py:4` |
| **D-05** | Fallo de OCI = **degradación controlada**, no error: `exito_con_advertencias` + `advertencias[]` | ✅ Cumplida | `src/errores.py:61`, `src/contracts/response.py:203`, `enums.py:210` |
| **D-06** | **Solo interfaz interactiva**, sin API REST. El sistema externo se sirve con el JSON en Object Storage | ✅ Cumplida | `app.py`; no hay framework HTTP en `requirements.txt` |
| **D-07** | Índice vectorial **persistente por `document_id`**: se indexa una vez y se reutiliza | ✅ Cumplida | `src/rag/vectorstore.py:2`, `indexacion.py:10`, `request.py:117` |
| **D-08** | Se usan **capas gratuitas**; si se agotan, el costo lo asume el equipo. Plan B = cambiar una variable de entorno | ✅ Cumplida (con matiz) | `src/llm_provider.py:16`, `src/seguridad/llm_client.py:38` |
| **D-09** | Embeddings del RAG con **e5 por la API de Hugging Face**, no con Gemini | ✅ Cumplida | `src/rag/embeddings.py:2`, `src/rag/configuracion.py:54` |
| **D-12** | Umbral de recuperación **configurable**, calibrado en **0.83** | ✅ Cumplida | `src/rag/configuracion.py:65`, `.env.example` |

**D-10 y D-11 no aparecen en el repositorio.** Si existieron, no dejaron rastro en código ni en
documentación; conviene no citarlas.

### Matices que importan

- **D-02 / D-08:** el score lo emite el verificador LLM; la cascada determinista de `src/fidelidad/`
  está implementada y testeada pero **no cableada al grafo** (`src/grafo.py:506-510`). Y no hay
  fallback *entre proveedores*: dentro de Groq sí hay cascada de tres modelos con fallback por cupo.
  Ver `docs/limitaciones-y-alcance.md`, puntos 1 y 8.
- **D-03:** el umbral y los reintentos son configurables; los valores actuales son `0.80` y `1`. El
  contador del grafo (`MAX_REINTENTOS_REDACTOR = 2`, `src/grafo.py:80`) cuenta *intentos totales*,
  no reintentos: 1 generación + 1 reintento.
- **D-06:** "sin API REST" no significa "sin contrato": la función principal expone exactamente el
  esquema de entrada/salida de la especificación, y el paquete queda persistido en OCI.

## 2. Decisiones de proceso (no numeradas en el gate)

| Decisión | Por qué | Dónde se ve |
|---|---|---|
| **Contrato congelado** con `extra="forbid"` y alias de entrada | Permite que cinco personas trabajen en paralelo sin pisarse, y que un campo mal escrito falle en vez de pasar en silencio | `src/contracts/`, `tests/test_contratos.py` |
| **El Supervisor clasifica con LLM; el ruteo es por reglas** | Un LLM evaluando el ruteo es caro, lento y no reproducible; las reglas se leen y se testean | `src/agentes/supervisor.py` + los `enrutar_*` de `src/grafo.py` |
| **HITL de una ronda** con contadores que se incrementan y **nunca se resetean** | Evita bucles infinitos y deja trazabilidad de cuántas veces intervino el humano | `src/grafo.py:80-81` |
| **OCI solo por nodos determinísticos**, vía servidor MCP | Ningún agente toca el bucket: el acceso queda auditable y acotado | `src/servidor_objeStorageOracle.py`, `src/Cliente_agemte.py` |
| **`main` es snapshot, `dev` es la rama viva** | Cada release es un `dev → main` con tag; `main` siempre es un estado entregable | tags `v1.0` y `v1.0.1` |
| **`arranque_demo.py` como respaldo de módulos opcionales** | Una demo que corre completa vale más que una app que se cae por una dependencia ausente | `src/arranque_demo.py`, `tests/test_arranque_demo.py` |
| **No hay fallback automático entre proveedores LLM** | Si el producto promete trazabilidad, hay que saber con qué modelo se generó | `src/llm_provider.py:16` |

## 3. Cómo se agrega una decisión nueva

1. Se escribe acá con un ID (`D-13`, `D-14`…) o en la sección de proceso si no toca contrato.
2. Cuatro campos: **contexto**, **decisión**, **consecuencia** y **dónde vive** (archivo:línea).
3. Si contradice una decisión anterior, no se borra la anterior: se marca *reemplazada por D-xx*.
4. Si toca el contrato congelado, necesita PR a `dev` y revisión del equipo antes de mergear.

Una decisión sin archivo y línea donde verificarse es una intención, no una decisión.

---

## Cómo verificar este documento

```bash
git grep -nE "D-(01|02|03|04|05|07|09|12)" -- src/
git grep -n "FORMATO_NO_DISPONIBLE_EN_MVP" -- src/
git grep -n "MAX_REINTENTOS_REDACTOR\|MAX_VUELTAS_MODIFICACION" -- src/grafo.py
git tag --list
```
