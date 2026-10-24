# Limitaciones y alcance — NuevaMente v1.0.1

> **Qué es este documento.** Declara lo que el sistema **no** hace hoy, por qué, y qué haría falta
> para cerrarlo. Está escrito para que cualquiera pueda verificarlo contra el código, no para
> justificarlo: cada punto trae el archivo y la línea donde se comprueba.
>
> **Referencia:** `main` @ `346f631` (tag `v1.0.1`). Fecha: 2026-10-24.
>
> Si algo no aparece acá, no es una omisión oculta: está implementado y cubierto por tests.

## Resumen

| # | Limitación | Impacto en la demo | Se cierra con |
|---|---|---|---|
| 1 | La cascada de fidelidad está implementada pero no cableada al grafo | El score lo emite el LLM, no el coseno | Inyectar `calculador_fidelidad` en `src/grafo.py` |
| 2 | Auth, cuotas y estilos del documento son respaldos de demo | No hay login ni límite por usuario | Módulos reales de `seguridad/` y `render_documento` |
| 3 | OCI no está disponible en la app pública | La demo de OCI corre en VM/local, no en Streamlit Cloud | Desplegar con Instance Principal |
| 4 | El índice vectorial es local (Chroma en disco) | Cada despliegue reconstruye su índice | Vector store gestionado |
| 5 | Formatos de entrada acotados a PDF, Markdown y texto | Sin OCR ni `.docx`/`.pptx` | OCR + conversores |
| 6 | Sin evaluación de calidad end-to-end con conjunto dorado | Hay 605 tests, no una métrica agregada | Set dorado con métricas |
| 7 | Sin persistencia de usuarios ni historial | Al recargar se pierde la sesión | Base de datos de corridas |
| 8 | Dependencia de cuotas gratuitas (Groq, HF Inference) | Latencia variable y límites diarios | Cuota pagada o proveedor propio |

---

## 1. La cascada de fidelidad está implementada, no cableada

**Qué pasa.** El `anclaje_fuente_score` que llega en el paquete lo produce el verificador LLM
(decisión D-02): una segunda llamada con rol distinto que clasifica cada afirmación como
soportada, parcial o no soportada. La cascada determinista —coseno contra los chunks y LLM solo
en la zona ambigua— existe completa en `src/fidelidad/` (`nucleo.py`, `extraccion.py`) y tiene
tests propios (`tests/test_fidelidad.py`), pero **el grafo no la usa**: `src/grafo.py:506-510`
construye el Crítico/Revisor sin pasarle `calculador_fidelidad`.

**Por qué importa.** El score depende del modelo y de la cuota, y no es reproducible bit a bit.
El puerto ya está definido (`CalculadorFidelidad` en `src/agentes/agente_critico_revisor.py:65`)
y el nodo lo acepta (`revisar_contenido(..., calculador_fidelidad=None)`), así que la integración
es de cableado, no de diseño.

**Qué se necesita.** Inyectar el calculador en la factory del grafo y agregar un test de
integración que verifique que el score del paquete sale de la cascada.

**Cómo verificarlo.**

```bash
git grep -n "calculador_fidelidad" -- src/
# aparece en src/agentes/*.py y en tests/ — nunca en src/grafo.py
```

---

## 2. Autenticación, cuotas y estilos del documento son respaldos de demo

**Qué pasa.** `src/arranque_demo.py` provee `requerir_login`, `consumir_corrida`,
`corridas_restantes`, `tipo_documento` y `html_documento` para cuando los módulos reales no
están disponibles. La app funciona de punta a punta, pero **no hay login real ni límite de
corridas por usuario** en la versión desplegada.

**Por qué está así.** Se prefirió una demo que corre completa antes que una app que se cae por
una dependencia opcional. El contrato está fijado por `tests/test_arranque_demo.py` (12 tests),
de modo que reemplazar el respaldo por el módulo real no rompe `app.py`.

**Qué se necesita.** Implementar los módulos reales y quitar el respaldo (o dejarlo solo como
fallback explícito en local).

---

## 3. La persistencia en OCI no está disponible en la app pública

**Qué pasa.** El servidor MCP (`src/servidor_objeStorageOracle.py`) autentica con
**Instance Principal** en la VM de OCI o con `~/.oci/config` en local (`OCI_LOCAL_DEV=1`).
Streamlit Community Cloud no ofrece ninguna de las dos, así que la app pública corre **sin**
persistencia en OCI. La demostración de OCI se hizo sobre la VM / entorno local con credenciales.

**Qué lo hace seguro.** El diseño de `status` impide mentir: si OCI falla, el paquete se emite
como `exito_con_advertencias`, nunca como éxito completo.

**Qué se necesita.** Desplegar la app donde haya Instance Principal (una VM de OCI) o inyectar
credenciales por secrets con un usuario de servicio acotado al bucket.

---

## 4. El índice vectorial es local

**Qué pasa.** Chroma persistente en `CHROMA_PATH` (por defecto `chroma_db/`), con una colección
por `document_id` (decisión D-07) y distancia coseno. No es un servicio gestionado: cada
instancia o despliegue construye su propio índice, y no hay índice compartido entre usuarios ni
entre réplicas.

**Qué se necesita.** Vector store gestionado (Chroma en servidor, pgvector u OCI AI Vector Store),
o indexación en el arranque del contenedor.

---

## 5. Formatos de entrada acotados

**Qué pasa.** Se procesan **PDF** (una cadena por página), **Markdown** (`.md`, `.markdown`) y
**texto** (`.txt`) — `src/rag/extraccion.py:24-25`. No hay OCR, así que un PDF escaneado no se
lee; y `.docx`, `.pptx` o HTML se rechazan con mensaje explícito
(*"usa PDF, Markdown o texto"*).

**Qué se necesita.** OCR (Tesseract o Document AI) para escaneados y conversores por formato.

---

## 6. No hay evaluación de calidad end-to-end con conjunto dorado

**Qué pasa.** Hay **605 tests** en 38 archivos: contrato, agentes con dobles, grafo, seguridad,
RAG y calibración. Lo que no existe es una métrica agregada sobre un conjunto de documentos y
perfiles reales: precisión de recuperación, comparación entre niveles de Bloom, o tasa de
paquetes aprobados sin intervención humana.

Hoy el único número de calidad es `anclaje_fuente_score`, y su origen es el LLM (ver punto 1).

**Por qué importa.** Sin conjunto dorado no se puede afirmar "mejoramos el retrieval" ni
comparar dos configuraciones de chunking con evidencia.

**Qué se necesita.** 10-20 documentos con paquetes esperados y métricas: precision@k, porcentaje
de afirmaciones soportadas, tiempo y tokens por etapa.

---

## 7. Sin persistencia de usuarios ni historial

**Qué pasa.** El estado de la sesión vive en `session_state` de Streamlit (48 usos en `app.py`).
No hay base de datos de usuarios, corridas ni historial de paquetes: al recargar, se pierde.

**Qué se necesita.** Una tabla de corridas. Los artefactos ya tienen dónde vivir (el bucket de
OCI, prefijos `generados/` y `generados/formateados/`).

---

## 8. Dependencia de servicios externos con cuota gratuita

- **LLM:** Groq con cascada `openai/gpt-oss-120b → openai/gpt-oss-20b → qwen/qwen3.8-27b` y
  fallback por cupo real (`src/seguridad/llm_client.py:38`). Si los tres modelos están sin cupo,
  la corrida falla con mensaje explícito.
- **Embeddings:** Hugging Face Inference, `intfloat/multilingual-e5-base` (768 dimensiones).
- **No hay fallback entre proveedores distintos**, y es deliberado (`src/llm_provider.py:16`):
  cambiar de proveedor es una decisión humana, para no perder la trazabilidad de qué modelo
  generó qué.

**Consecuencia.** Latencia variable y límites diarios. Para uso sostenido se necesita cuota
pagada o un modelo servido por el propio equipo.

---

## Lo que sí está (y se verifica en cinco minutos)

- **Contrato congelado** con `extra="forbid"`, alias de entrada y forma canónica corta
  (`src/contracts/`). Un campo mal escrito falla, no pasa en silencio.
- **Validación determinística antes de cualquier llamada al LLM**: `nodo_validacion` y
  `nodo_validacion_solicitud` (`src/grafo.py:265,282`) validan tema, historial y campos tipados.
- **HITL de una ronda** con contadores que se incrementan y nunca se resetean
  (`intentos_redactor`, `vueltas_modificacion`).
- **Seguridad de red y de coste:** guardia de red con allowlist y bloqueo de IPs privadas,
  rate limiter por modelo, permisos (`src/seguridad/`).
- **OCI vía MCP:** ningún agente toca el bucket; solo los nodos determinísticos de ingesta y
  guardado (`src/servidor_objeStorageOracle.py`, `src/Cliente_agemte.py`).
- **605 tests en verde** sobre `main` (`346f631`).

---

## Trabajo futuro, en orden de impacto

1. **Cablear `src/fidelidad/` al Crítico** — cierra el punto 1 y vuelve el score reproducible.
2. **Conjunto dorado con métricas** — cierra el punto 6; es lo que permite hablar de mejora con números.
3. **Auth real y cuotas** — cierra el punto 2.
4. **Índice vectorial compartido** — cierra el punto 4.
5. **OCR y `.docx`** — cierra el punto 5.
6. **Historial de corridas** — cierra el punto 7.

---

## Cómo verificar este documento

```bash
python -m pytest tests/ -q                        # 605 passed
git grep -n "calculador_fidelidad" -- src/        # no aparece en src/grafo.py
git grep -n "EXTENSIONES_" -- src/rag/extraccion.py
git grep -n "_DEFAULT_CHAIN" -- src/seguridad/llm_client.py
git grep -n "session_state" -- app.py | wc -l     # 48
```
