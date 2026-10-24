# Métricas de fidelidad y calibración — NuevaMente

> **Qué es este documento.** Cómo se mide que el contenido generado esté anclado a la fuente, cómo
> se fijaron los umbrales y cómo se reproducen las cuentas. Es el respaldo numérico de la promesa
> central del proyecto: *fidelidad verificable*.
>
> **Referencia:** `main` @ `346f631` (tag `v1.0.1`). Fecha: 2026-10-24.

## 1. Dos números distintos que no hay que confundir

| Métrica | Pregunta que responde | Umbral | Variable |
|---|---|---|---|
| `UMBRAL_RETRIEVAL` | ¿Este chunk habla del tema que se preguntó? | **0.83** (D-12) | `UMBRAL_RETRIEVAL` |
| `FIDELIDAD_UMBRAL` | ¿Lo que se generó está soportado por la fuente? | **0.80** (D-03) | `FIDELIDAD_UMBRAL` |

El primero filtra **entrada** (qué fragmentos entran al contexto). El segundo evalúa **salida** (qué
tanto del contenido se puede sostener con esos fragmentos). Confundirlos es el error más fácil de
cometer al leer los logs.

## 2. `anclaje_fuente_score` (D-02)

1. Del paquete generado se extraen las **afirmaciones verificables** (una por ítem, o varias si el
   ítem es largo).
2. Un **verificador separado** —rol distinto, contexto distinto— recibe **solo** las afirmaciones y
   los chunks recuperados. Nunca el prompt del redactor ni el perfil del destinatario.
3. Cada afirmación se clasifica `soportada`, `parcialmente_soportada` o `no_soportada`.
4. **`score = (soportadas + 0.5 × parciales) ÷ total`**, en escala 0.0–1.0.

**Por qué así.** El riesgo R-02 de la especificación era que el mismo modelo que redacta se ponga la
nota: circular, y no detecta nada. Al aislar al verificador, el número significa algo y se puede
defender ante un evaluador.

**Dónde vive.** El puerto está en `src/agentes/agente_critico_revisor.py:65` (`CalculadorFidelidad`)
y el nodo en `src/agentes/critico_revisor.py`. El campo del contrato es obligatorio:
`src/contracts/response.py:98`.

**Prueba de que mide algo real (AC-11.3).** Tomar un paquete correcto, inyectarle a mano una
afirmación que no está en el documento y comprobar que el score baja. Si no baja, el verificador no
sirve.

## 3. Qué pasa si el score queda bajo (D-03)

```
score ≥ 0.80  →  paquete aceptado
score < 0.80  →  se regenera UNA vez con más contexto (FIDELIDAD_MAX_REINTENTOS=1)
                 ├─ segundo score ≥ 0.80  →  aceptado
                 └─ segundo score < 0.80  →  claridad_pedagogica = "Requiere revisión"
                                             y status = "exito_con_advertencias"
```

El `0.80` **es decisión del equipo, no un dato del hackathon**: el documento no fija ningún umbral.
El reintento está acotado a uno porque tres generaciones encadenadas en una demo de 90 segundos es
un riesgo de tiempo real. Ambos valores son configurables por `.env`.

## 4. La cascada determinista (implementada, no cableada al grafo)

`src/fidelidad/nucleo.py` implementa una cascada que combina los dos métodos en conflicto:

| Coseno afirmación ↔ chunks | Qué hace | Costo |
|---|---|---|
| `≥ 0.85` | **Soportada** sin llamar al LLM | 0 |
| `0.55 – 0.85` | Zona ambigua → **decide el verificador LLM** | 1 llamada |
| `< 0.55` | **No soportada** sin llamar al LLM | 0 |

Con las bandas de la calibración del 29/09, **el 48% de las 40 afirmaciones de prueba llega al
juez**: se ahorra cerca de la mitad de las llamadas y se conserva el juicio donde hace falta.

Las bandas son **provisionales**: `0.85 / 0.55` es lo que hay en `.env.example`, pero la calibración
sugiere `0.8885 / 0.8457` (con `0.85` se aprobarían sin juez 8 de cada 10 afirmaciones inventadas
del tema). Se cierran en T3-04.

> ⚠️ **Estado real:** la cascada tiene tests propios (`tests/test_fidelidad.py`) pero el grafo
> construye el Crítico sin inyectarle el calculador (`src/grafo.py:506-510`). En la demo, el score
> lo emite el verificador LLM. Ver `docs/limitaciones-y-alcance.md`, punto 1.

## 5. Calibración del umbral de recuperación (D-12)

**Fecha:** 29/09/2026. **Insumos:** 69 consultas sobre 5 guías de certificación. **Modelo:**
`intfloat/multilingual-e5-base`.

| Tipo de consulta | Puntaje mínimo observado |
|---|---|
| Del tema (descriptivas) | **0.858** |
| Ajenas al tema | hasta **0.818** |

Con consultas descriptivas, **0.83 separa sin errores**. El plan original decía 0.78.

**El límite conocido:** con consultas de una o dos palabras ningún umbral separa. Con 0.83 quedan
fuera `Kanban` (0.797) e `impedimentos` (0.818), y no entra ninguna ajena (la más alta,
`contabilidad`, marca 0.824). De ahí que el Investigador reformule en vez de buscar con la palabra
suelta.

## 6. Higiene de fragmentos

Los chunks cortos se parecen a cualquier consulta y ensucian el ranking:

- **`CHUNK_FUSION = 300`**: los fragmentos de menos de 300 caracteres se unen a un vecino. En la
  calibración, fragmentos así eran el *mejor* resultado de muchas consultas ajenas (por ejemplo,
  `contabilidad` contra uno de 122 caracteres).
- **`CHUNK_MINIMO = 100`**: los que quedan sueltos y son más cortos no se indexan. La portada de una
  guía (28 caracteres) salía primera en consultas ajenas (T2-06).
- **`CHUNK_SIZE = 1000` / `CHUNK_OVERLAP = 150`**: el solape evita cortar una idea entre dos
  fragmentos.

Los cuatro entran en la firma del índice: cambiarlos obliga a reindexar.

## 7. Cómo reproducir la calibración

```bash
# Con e5 real (gasta cuota de Hugging Face: indexa lo que falte y embebe cada consulta una vez)
python scripts/calibrar_e5.py --datos scripts/datos/calibracion_e5.json \
                              --insumos ../../04_insumos --salida CARPETA

# Sin red ni token: embeddings de bolsa de palabras. Revisa el flujo, no los números
python scripts/calibrar_e5.py --simular
```

El script **no decide nada**: deja los datos y sugiere umbrales con las reglas a la vista
(`src/rag/calibracion.py`). Los datos de entrada están en `scripts/datos/calibracion_e5.json`
(guias, consultas, afirmaciones).

## 8. Lo que estas métricas no cubren

- No hay conjunto dorado con paquetes esperados, así que no hay precision@k agregada ni comparación
  entre configuraciones de chunking con evidencia.
- No se mide calidad pedagógica (¿el nivel de Bloom es el correcto para este perfil?) más allá de la
  observación cualitativa del Crítico.
- No se mide latencia ni costo por etapa.

Ver `docs/limitaciones-y-alcance.md`, punto 6.

---

## Cómo verificar este documento

```bash
git grep -n "UMBRAL_RETRIEVAL_POR_DEFECTO\|CHUNK_FUSION_POR_DEFECTO\|CHUNK_MINIMO_POR_DEFECTO" -- src/rag/configuracion.py
git grep -n "BANDA_ALTA\|BANDA_BAJA" -- src/fidelidad/nucleo.py
git grep -n "FIDELIDAD_UMBRAL\|FIDELIDAD_MAX_REINTENTOS" -- src/config.py
python -m pytest tests/test_fidelidad.py tests/test_rag_calibracion.py -q
```
