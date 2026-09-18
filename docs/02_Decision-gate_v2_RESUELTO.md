# NuevaMente — Decision Gate v2 · RESUELTO

**Proyecto:** NuevaMente — Hackathon ONE G10 (Oracle Next Education & Alura)
**Fecha:** 18 de septiembre de 2026
**Estado:** ✅ **Las 7 decisiones bloqueantes están cerradas.** Fase 2 (arquitectura) desbloqueada.
**Documento anterior:** `nuevamente-especificacion-funcional.md` (§1 a §12)

---

## 0. Resumen ejecutivo de una página

| Decisión | Resuelta como | Impacto |
|---|---|---|
| **Q-08** Formatos pedagógicos | **4 de 5:** Flashcards, Tutorial, TL;DR, Quiz | +8 h sobre el plan base |
| **Q-10** Cálculo de fidelidad | **Agente verificador separado**, escala 0.0–1.0 | Diferenciador defendible |
| **Q-11** Umbral y acción | **0.80 + 1 reintento**, luego marcar | Control real, no reporte |
| **Q-01** Vías de entrada | **Dos modos en la acción principal** (archivo o texto) | +3 h sobre el plan base |
| **Q-14** Fallo de OCI | **Degradación controlada** | Protege la demo en vivo |
| **Q-15** Superficie | **Sólo interfaz** | Libera ~10 h |
| **Q-06** Índice vectorial | **Persistente por `document_id`** | Demo 4× más rápida |
| **Q-20** Costo del LLM | **Capas gratuitas; si no, lo asume el equipo** | Condiciona proveedor |

**Advertencia principal, y la razón por la que este documento existe:** con estas decisiones el alcance quedó **entre 25% y 35% por encima del presupuesto de horas disponible**. La §5 dice exactamente qué se cae y cuándo se decide. No es un problema que se resuelva trabajando más rápido.

---

## 1. Las 7 decisiones, registradas

### D-01 · Q-08 — Formatos pedagógicos del MVP

**Decisión: se implementan 4 de los 5 formatos.**

| Formato | Estado MVP | Origen del esquema |
|---|---|---|
| Flashcards de Memorización | ✅ Implementado | **Documentado en la fuente** (p.5) |
| Guía Práctica Paso a Paso (Tutorial) | ✅ Implementado | Definido por el equipo (§2.2) |
| Resumen Ejecutivo (TL;DR) | ✅ Implementado | Definido por el equipo (§2.3) |
| Quiz Interactivo con Justificaciones | ✅ Implementado | Definido por el equipo (§2.4) |
| Guion de Clase / Video | ⬜ Declarado, no implementado | Definido por el equipo (§2.5), listo por si sobra tiempo |

El quinto formato **queda declarado en el contrato** y devuelve un error tipificado `FORMATO_NO_DISPONIBLE_EN_MVP`. Esto es deliberado: demuestra que el contrato fue diseñado para los 5 y que la omisión es una decisión de alcance, no un descuido.

> **Efecto sobre la evaluación:** la casilla 4 del Checklist exige ≥2 formatos. Con 4, hay margen de sobra y los escenarios de demostración pueden ser mucho más expresivos.

### D-02 · Q-10 — Cómo se calcula `anclaje_fuente_score`

**Decisión: agente verificador separado.**

Mecanismo acordado:

1. Del paquete generado se extraen las **afirmaciones verificables** (una por ítem, o varias si el ítem es largo).
2. Una **segunda llamada al LLM**, con un rol distinto al del redactor, recibe **únicamente**: las afirmaciones + los chunks recuperados del documento original. No recibe el prompt de redacción ni el perfil ni el nicho.
3. Clasifica cada afirmación como `soportada` / `parcialmente_soportada` / `no_soportada`.
4. **`anclaje_fuente_score` = afirmaciones soportadas ÷ afirmaciones totales.** Escala **0.0 a 1.0**, dos decimales.

Las parcialmente soportadas cuentan como **0.5**.

**Por qué esta forma y no otra:** el riesgo R-02 de la especificación era que el mismo modelo que redacta se ponga la nota. Eso es circular y no detecta nada. Al aislar al verificador —rol distinto, contexto distinto, sin acceso a la intención del redactor— el número pasa a significar algo, y **se puede defender frente a un evaluador que pregunte cómo se calcula**.

**Beneficio lateral:** este verificador **es** el "Agente Crítico/Revisor" del diferencial opcional de multi-agente (p.6). Se obtienen dos cosas con un solo desarrollo.

**Costo:** una llamada adicional al LLM por generación.

**Prueba de que el mecanismo mide algo real (AC-11.3):** tomar un paquete correcto, inyectarle a mano una afirmación que no está en el documento, y verificar que el score baja. Si no baja, el verificador no sirve. **Esta prueba debe estar en la demostración** — es el momento más convincente del pitch.

### D-03 · Q-11 — Umbral y acción correctiva

**Decisión: umbral 0.80, un reintento, luego entregar marcado.**

```
score ≥ 0.80  →  paquete aceptado
score < 0.80  →  regenerar UNA vez con contexto ampliado (más chunks)
                 │
                 ├─ segundo score ≥ 0.80  →  aceptado
                 └─ segundo score < 0.80  →  entregado con
                                             claridad_pedagogica = "Requiere revisión"
                                             y advertencia explícita en la respuesta
```

**El 0.80 es una decisión del equipo, no un dato de la fuente.** El documento del Hackathon no fija ningún umbral. Debe quedar documentado como tal en el README, y ser configurable.

El reintento está acotado a **uno** por una razón concreta: con 90 a 120 segundos de demo en vivo, tres generaciones encadenadas en el peor caso es un riesgo de tiempo real.

### D-04 · Q-01 — Vías de entrada

**Decisión: la acción principal acepta dos modos.**

| Modo | Entrada | Quién lo usa |
|---|---|---|
| **A · Archivo** | PDF, Markdown o texto plano | La interfaz, cuando el usuario carga un archivo |
| **B · Texto embebido** | `documento_titulo` + `documento_contenido` | El contrato oficial de la p.4; pruebas y ejemplos documentados |

Internamente convergen: el modo A extrae el texto y continúa por el mismo camino que el modo B. **Un solo núcleo, dos puertas.**

**Por qué vale los ~3 h extra:** si un evaluador toma el Ejemplo de Solicitud de la p.4 y lo prueba tal cual, funciona. Y si carga un PDF, también. Se eliminan las dos formas de quedar mal.

### D-05 · Q-14 — Comportamiento ante fallo de OCI

**Decisión: degradación controlada.**

| Situación | `status` | `almacenamiento_oci.status_upload` |
|---|---|---|
| Todo bien | `"exito"` | `"completado"` |
| Generación bien, carga a OCI falla | `"exito_con_advertencias"` | `"fallido"` |
| Falla la generación | `"error"` | `"no_intentado"` |

La respuesta incluye además un arreglo `advertencias[]` con el detalle legible.

**Importante para la evaluación:** la casilla 6 exige "integración **activa y funcional**". La degradación es una **red de seguridad, no el camino principal**. La demostración debe mostrar el camino feliz, con el objeto visible en la consola de OCI. La degradación se menciona como robustez, no como excusa.

### D-06 · Q-15 — Superficie del sistema

**Decisión: sólo interfaz interactiva.**

- La **acción principal** existe como **una función única** con exactamente el contrato de entrada/salida de la p.4.
- La interfaz la invoca. No se construye API REST.
- El Checklist (casilla 5) dice "interfaz interactiva **o** API REST operativa" — es una disyunción explícita, y los Resultados esperados (p.3) dicen "Endpoint **o** interfaz". La decisión está dentro de lo que el documento permite.
- El actor **S1 (sistema externo consumidor)** queda servido por el **JSON persistido en Object Storage**, que es legible desde fuera.

> Si sobran horas en la última semana —cosa que la §5 dice que no va a pasar— exponer la función como API REST cuesta ~8-12 h. Queda como `SHOULD`, no como plan.

### D-07 · Q-06 — Ciclo de vida del índice vectorial

**Decisión: persistente por documento.**

- Se indexa **una vez** por `document_id`.
- Todas las generaciones sobre ese documento **reutilizan** el índice.
- Clave de caché: `document_id` (hash del contenido, para que el mismo documento cargado dos veces no se reindexe).

**Por qué importa más de lo que parece:** la demostración genera 4 escenarios sobre el mismo documento. Con índice efímero, eso es reindexar 4 veces frente al jurado — 4× latencia y 4× consumo de embeddings, dentro de una ventana de 90 segundos. Con índice persistente, se indexa una vez y las 4 generaciones salen seguidas.

### D-08 · Q-20 — Costo del LLM *(respondida por el equipo)*

**Decisión: se usan capas gratuitas; si se agotan, el costo lo asume el equipo.**

**Consecuencia que hay que planificar ahora, no el 1 de octubre:**

- La elección de proveedor (fase de arquitectura) queda **restringida a los que tengan capa gratuita usable**.
- Con 3 personas iterando prompts durante 2 semanas, **las capas gratuitas se agotan**. Es predecible, no es mala suerte.
- **Acción:** definir un **proveedor de respaldo** desde el día 1 y no acoplar el código a un solo proveedor (NFR-SCA-02). Si el principal se agota el 1 de octubre, el plan B debe ser cambiar una variable de entorno, no reescribir.
- **Acción:** fijar un presupuesto de iteraciones por persona y usar **documentos cortos** para iterar prompts, reservando los documentos completos para las pruebas finales.

---

## 2. Esquemas JSON de `contenido_adaptado.items[]`

Esto es lo que la ambigüedad A-08 dejaba sin definir. **Son decisiones del equipo**, no datos de la fuente, salvo el primero.

### 2.0 · Envoltura común a todos los formatos

```json
"contenido_adaptado": {
  "titulo": "string",
  "introduccion_contextualizada": "string",
  "items": [ /* estructura según formato */ ]
}
```

`titulo` e `introduccion_contextualizada` existen en **todos** los formatos — están en el ejemplo oficial de la p.5.

### 2.1 · Flashcards de Memorización  🟢 *documentado en la fuente (p.5)*

```json
{
  "frente": "Que es una VCN en Oracle Cloud?",
  "dorso": "Es tu red virtual privada y personalizada dentro de la nube de Oracle.",
  "pista_didactica": "Piensa en ella como el terreno cercado donde residen tus servidores."
}
```

**No se modifica ni un campo.** Es el único esquema que el documento oficial define, y es la referencia de estilo para los demás.

### 2.2 · Guía Práctica Paso a Paso (Tutorial)  🟡 *definido por el equipo*

```json
{
  "paso_numero": 1,
  "titulo_paso": "Crear la Virtual Cloud Network",
  "instruccion": "Desde la consola de OCI, abre el menu de navegacion y selecciona Networking, luego Virtual Cloud Networks.",
  "resultado_esperado": "Veras la lista de VCN del compartimento, vacia si es la primera vez.",
  "advertencia": "Verifica que estas en la region correcta antes de crear la VCN: los recursos no se mueven entre regiones."
}
```

| Campo | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `paso_numero` | entero ≥ 1 | Sí | Consecutivo, sin saltos |
| `titulo_paso` | texto | Sí | Corto, accionable |
| `instruccion` | texto | Sí | Qué hace el estudiante |
| `resultado_esperado` | texto | Sí | Cómo sabe que le salió bien |
| `advertencia` | texto o `null` | No | Error común o riesgo del paso |

**Criterio de diseño:** `resultado_esperado` es lo que separa un tutorial de una lista de instrucciones. Permite que el estudiante se autoverifique sin ayuda.

### 2.3 · Resumen Ejecutivo (TL;DR)  🟡 *definido por el equipo*

```json
{
  "punto_clave": "La VCN aisla la red de la empresa dentro de la nube de Oracle.",
  "implicacion": "Permite cumplir requisitos de segregacion de red sin comprar hardware propio.",
  "relevancia_negocio": "Reduce el tiempo de aprovisionamiento de entornos de semanas a horas y elimina el costo de capital en equipos de red."
}
```

| Campo | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `punto_clave` | texto | Sí | El hecho técnico, en una frase |
| `implicacion` | texto | Sí | Qué significa en la práctica |
| `relevancia_negocio` | texto | Sí | Por qué le importa a quien decide presupuesto |

**Criterio de diseño:** el perfil destinatario de este formato es `Gestor / Ejecutivo (No Técnico)`. Un resumen que sólo comprime el texto técnico no le sirve. Los tres campos obligan a la cadena **hecho → consecuencia → valor**, que es como piensa ese perfil.

> **Este formato es el que gana el pitch.** El contraste entre un paquete de Flashcards para un principiante y este mismo documento como TL;DR ejecutivo es instantáneamente legible para un jurado no técnico.

### 2.4 · Quiz Interactivo con Justificaciones  🟡 *definido por el equipo*

```json
{
  "pregunta": "Que componente de una VCN controla el trafico de entrada y salida mediante reglas?",
  "opciones": [
    { "id": "a", "texto": "Internet Gateway" },
    { "id": "b", "texto": "Security Lists" },
    { "id": "c", "texto": "Tabla de enrutamiento" },
    { "id": "d", "texto": "Subred privada" }
  ],
  "respuesta_correcta": "b",
  "justificacion": "Las Security Lists son listas de reglas que definen que trafico puede entrar (ingress) o salir (egress) de la red.",
  "analisis_distractores": "El Internet Gateway da salida a internet pero no filtra por reglas; la tabla de enrutamiento decide rutas, no permisos; la subred es un segmento de red, no un control de trafico."
}
```

| Campo | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `pregunta` | texto | Sí | Una sola idea por pregunta |
| `opciones` | arreglo de 3 a 5 | Sí | `id` en minúscula, `texto` sin pistas de longitud |
| `respuesta_correcta` | texto | Sí | Debe coincidir con un `id` de `opciones` |
| `justificacion` | texto | Sí | **Exigido por el nombre del formato en la fuente** (p.2) |
| `analisis_distractores` | texto o `null` | No | Por qué las otras opciones fallan |

**Regla de validación no negociable:** `respuesta_correcta` debe existir entre los `id` de `opciones`. Es el error más común en quizzes generados por LLM y hay que validarlo en el esquema, no confiar en el modelo.

**Criterio de diseño:** `analisis_distractores` es lo que convierte el quiz en material de estudio en vez de un examen. También es la base directa del diferencial opcional de retroalimentación en tiempo real (p.6), si sobra tiempo.

### 2.5 · Guion de Clase / Video  ⬜ *definido, NO implementado en el MVP*

```json
{
  "bloque_numero": 1,
  "titulo_bloque": "Apertura: por que necesitas una red privada en la nube",
  "duracion_estimada_segundos": 90,
  "guion": "Texto literal que el instructor dice frente a camara.",
  "apoyo_visual": "Diagrama de una VCN con dos subredes, una publica y una privada."
}
```

Queda **listo para implementar** si aparecen horas libres. No entra en el plan.

### 2.6 · Campo opcional de anclaje por ítem — *recomendación*

**No está decidido. Lo propongo y ustedes deciden.**

Agregar a **cada ítem**, en todos los formatos:

```json
"anclaje": ["chunk_003", "chunk_007"]
```

**Qué aporta:**

1. El agente verificador (D-02) recibe el trabajo medio hecho: ya sabe contra qué chunks contrastar cada afirmación, en vez de buscar entre todos.
2. Convierte el `anclaje_fuente_score` de un número opaco en algo **señalable en pantalla**: *"esta tarjeta sale de la página 3, párrafo 2"*. En un pitch de 5 minutos, poder señalar el origen de una afirmación es más persuasivo que mostrar un 0.98.
3. Es el `FR-FID-04` de la especificación, que estaba clasificado como `COULD`.

**Qué cuesta:** ~2 h, más algunos tokens extra por generación. Requiere que `FR-RAG-06` (metadatos de chunk) esté hecho, que ya es `MUST`.

**Mi recomendación: háganlo.** Es la mejor relación valor/esfuerzo que queda en la lista, y ataca directamente el riesgo R-02.

---

## 3. Contrato de error *(resuelve Q-12 / A-15)*

El documento fuente sólo trae el ejemplo de éxito. Este contrato es **decisión del equipo**.

### 3.1 · Valores de `status`

| Valor | Cuándo |
|---|---|
| `"exito"` | Todo salió bien, incluida la carga a OCI |
| `"exito_con_advertencias"` | El paquete se generó, pero algo no crítico falló (p. ej. la carga a OCI, o el score quedó bajo el umbral tras el reintento) |
| `"error"` | No hay paquete que entregar |

### 3.2 · Forma de la respuesta de error

```json
{
  "status": "error",
  "error": {
    "codigo": "DOCUMENTO_NO_SOPORTADO",
    "mensaje_usuario": "Ese archivo no se puede procesar. Aceptamos PDF, Markdown y texto plano.",
    "etapa": "ingesta",
    "campo": "documento_contenido"
  }
}
```

### 3.3 · Catálogo mínimo de códigos

| Código | Etapa | Mensaje al usuario (idea) |
|---|---|---|
| `DOCUMENTO_NO_SOPORTADO` | ingesta | Formato no admitido; se listan los aceptados |
| `DOCUMENTO_VACIO` | ingesta | No se pudo extraer texto legible del archivo |
| `DOCUMENTO_DEMASIADO_GRANDE` | ingesta | Supera el límite; se indica el límite |
| `PARAMETRO_INVALIDO` | validación | Se nombra el campo y los valores admitidos |
| `FORMATO_NO_DISPONIBLE_EN_MVP` | validación | Ese formato no está en esta versión |
| `FALLO_INDEXACION` | indexación | No se pudo preparar el documento; reintentar |
| `FALLO_LLM` | generación | El servicio de IA no respondió; reintentar |
| `SALIDA_INVALIDA` | generación | La respuesta no cumplió el esquema tras los reintentos |
| `FALLO_PERSISTENCIA` | persistencia | ⚠ **No produce `error`** — produce `exito_con_advertencias` (D-05) |

**Regla transversal (NFR-SEC-02):** `mensaje_usuario` nunca contiene trazas, rutas ni nombres de servicios internos. El detalle técnico va al log, no a la pantalla.

---

## 4. Ambigüedades restantes, resueltas por defecto

Estas eran menores. Las cierro con el criterio más conservador; **avísenme si alguna no les cuadra**.

| ID | Ambigüedad | Resolución adoptada |
|---|---|---|
| **A-03 / A-04** | Forma canónica de perfiles y formatos | El contrato acepta la **forma larga** (`"Principiante / Transición de Carrera"`) **y** la abreviada del ejemplo (`"Principiante"`). Se normaliza internamente. Así el Ejemplo de Solicitud oficial funciona tal cual. |
| **A-05** | ¿El nicho aparece en `metadatos`? | **Sí**, se agrega `metadatos.nicho_aplicado`. El ejemplo de la p.5 lo omite, pero perfil y formato sí están, y la asimetría no tiene justificación. Agregar un campo no rompe a ningún consumidor. |
| **A-06** | `nivel_detalle` | **Se implementa**, con tres valores: `"Didactico"` (el del ejemplo), `"Estandar"`, `"Profundo"`. Modula extensión y densidad, **independiente del perfil**, que modula el lenguaje. Se refleja en `metadatos.nivel_detalle_aplicado`. |
| **A-07** | Obligatoriedad de parámetros | `documento_titulo`, `documento_contenido` (o archivo), `perfil_destinatario` y `formato_salida` son **obligatorios**. `nicho_sector` por defecto `"General"`; `nivel_detalle` por defecto `"Estandar"`. |
| **A-09** | `prerrequisitos` ausente del contrato | **Se agrega** `metadatos.prerrequisitos` como arreglo de texto. La p.2 lo exige explícitamente; su ausencia en el ejemplo de la p.5 se trata como omisión del ejemplo, no como decisión. Cierra la única brecha real de la matriz (H-10). |
| **A-11** | Un solo `objeto_id` para dos artefactos | `almacenamiento_oci` se amplía: `{ bucket, objeto_id, objeto_documento_original, status_upload }`. Se conserva `objeto_id` con el significado del ejemplo (el JSON generado) para no romper el contrato documentado. |
| **A-14** | 3 escenarios vs 3 ejemplos | **Se satisfacen ambas lecturas**: 3+ escenarios sobre un documento común, **y** al menos un segundo documento distinto entre los ejemplos documentados. |
| **A-16** | Agentes obligatorios vs opcionales | Las tres responsabilidades (planificar, redactar, revisar) son obligatorias. El **verificador de D-02 ya es un agente autónomo real**, así que el sistema queda a medio camino del diferencial multi-agente sin costo adicional. |

---

## 5. ⚠ Realidad de presupuesto — léase antes de empezar a programar

### 5.1 · Lo que hay

| Recurso | Valor |
|---|---|
| Días calendario | **14** (18 sept → 2 oct) |
| Días con documentos reales | **9** (llegan el 23 sept) |
| Personas comprometidas | **3** (la cuarta no entra en el plan) |
| Horas por persona por día | 3 |
| **Presupuesto total** | **90 h** (lun-vie) a **126 h** (todos los días) |
| **Presupuesto realista**, descontando coordinación y arranque | **~90 a 110 h** |

### 5.2 · Lo que cuesta lo decidido

| Bloque | Horas est. |
|---|---|
| Núcleo RAG (ingesta, chunking, embeddings, vector store, recuperación) | 15 |
| 4 formatos (esquemas + prompts + renderizado + pruebas) | 23 |
| Agente verificador + umbral + reintento | 14 |
| Dos modos de entrada | 6 |
| Contrato tipado + validación entrada/salida | 8 |
| Persistencia OCI + degradación controlada | 11 |
| Interfaz | 12 |
| Manejo de errores | 5 |
| **D11: README, diagrama, 3 ejemplos, notebook** | **18** |
| Pitch: guion, ensayo, grabación de respaldo | 8 |
| Integración y corrección de fallas | 15 |
| **TOTAL** | **≈ 135 h** |

### 5.3 · El problema, dicho sin rodeos

**135 h de alcance contra 90-110 h de capacidad. Están entre 25% y 35% por encima.**

Esto no se arregla trabajando más rápido. Se arregla decidiendo qué se cae — y la diferencia entre decidirlo **hoy** y descubrirlo el 30 de septiembre es la diferencia entre entregar algo completo y entregar cuatro cosas a medias.

Las estimaciones son mías y pueden estar infladas un 20%. Aun en el mejor caso, el margen es cero.

### 5.4 · Plan propuesto, con punto de corte explícito

**Semana 1 — del 18 al 25 de septiembre · Rebanada vertical completa**

Un solo camino funcionando de extremo a extremo, con **2 formatos** (Flashcards + Tutorial):
ingesta → chunking → embeddings → vector store → recuperación → generación → verificador → validación → **OCI** → interfaz.

> Si OCI no está funcionando el **23 de septiembre**, es la alarma más importante del proyecto: es la única casilla del Checklist sin sustituto posible.

**Semana 2 — del 26 de septiembre al 2 de octubre**

- 26-27 sept: agregar TL;DR y Quiz.
- 28-29 sept: documentación, diagrama, 3 ejemplos, notebook.
- 30 sept - 1 oct: pitch, ensayo, **grabación de respaldo de la demo**.
- 2 oct: entrega.

**🔴 PUNTO DE CORTE — 29 de septiembre**

Si a esa fecha la rebanada vertical no está completa y documentada:

1. **Cae el Quiz** → se vuelve a 3 formatos (libera 8 h).
2. Si aún no alcanza, **cae TL;DR** → 2 formatos, el mínimo del Checklist (libera 7 h más).
3. **Nunca se sacrifica D11** (documentación, diagrama, ejemplos). Son 3 de las 8 casillas. Un sistema perfecto sin README pierde 37,5% de la evaluación.

### 5.5 · La regla que más protege el pitch

**Graben la demo en video el 1 de octubre.** Cinco minutos con jurado en vivo, red ajena y un LLM no determinista es un escenario donde algo falla. Si la demo en vivo se cae, se pone el video y se sigue hablando. Cuesta 2 horas y elimina el riesgo R-09 completo.

---

## 6. Qué sigue

### 6.1 · Desbloqueado — fase 2 puede empezar

Con estas decisiones, la arquitectura ya se puede diseñar. Lo que toca decidir ahí (y **sólo** ahí): proveedor de LLM y de embeddings, vector store, framework de orquestación, framework de interfaz, librería de validación tipada, estrategia de chunking y `k` de recuperación, estructura del repositorio.

### 6.2 · Pendiente del equipo, esta semana

| # | Acción | Responsable | Fecha |
|---|---|---|---|
| 1 | Confirmar estado de la cuenta OCI: ¿trial o Always Free? ¿cuándo vence? ¿home region? ¿bucket creado? | — | 19 sept |
| 2 | Poner las credenciales de OCI en manos de **al menos 2 personas** | — | 19 sept |
| 3 | Preguntar a los organizadores si existe ejemplo de salida para Tutorial, Quiz, TL;DR y Guion | — | 19 sept |
| 4 | Conseguir los documentos técnicos de prueba | — | 23 sept |
| 5 | Elegir proveedor de LLM **principal y de respaldo**, ambos con capa gratuita | — | 22 sept |
| 6 | Decidir si se adopta el campo `anclaje` por ítem (§2.6) | — | 22 sept |
| 7 | Aprobar o corregir §1 a §10 de la especificación funcional | — | 22 sept |

### 6.3 · Riesgos que cambiaron con estas decisiones

| Riesgo | Antes | Ahora |
|---|---|---|
| **R-02** Score circular | 🔴 Alto | 🟢 **Mitigado** por D-02 (verificador aislado) |
| **R-06** OCI en ruta crítica | 🟠 Medio-Alto | 🟢 **Mitigado** por D-05 (degradación) |
| **R-15** Re-indexación redundante | 🟡 Bajo-Medio | 🟢 **Mitigado** por D-07 (índice persistente) |
| **R-01** Formatos sin estructura | 🔴 Alto | 🟢 **Cerrado** por §2 (esquemas definidos) |
| **R-10** Subestimar documentación | 🔴 Alto | 🔴 **Sigue alto** — es el riesgo N.º 1 del proyecto |
| **R-13** Proveedor único de LLM | 🟠 Medio | 🔴 **Subió** — D-08 lo hace más probable. Exige plan B |
| **Nuevo · R-17** Alcance sobre presupuesto | — | 🔴 **Alto** — 25-35% de sobrecarga (§5) |

---

**Estado del gate:** ✅ **ABIERTO.** Las 7 decisiones bloqueantes están cerradas y los esquemas que faltaban están definidos.

**Lo único que queda por aprobar** es §1 a §10 de la especificación funcional — es decir, confirmar que la descripción del producto es correcta. Eso no bloquea empezar a diseñar la arquitectura.
