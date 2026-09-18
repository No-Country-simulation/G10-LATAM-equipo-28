# NuevaMente — Análisis de la propuesta de Marely + Configuración intercambiable de LLM

**Fecha:** 18 de septiembre de 2026
**Documentos previos:** `nuevamente-especificacion-funcional.md`, `02_Decision-gate_v2_RESUELTO.md`

---

# PARTE 1 · Propuesta de Marely Cárcamo

## Veredicto corto

**No es escueta. Es la mejor contribución técnica que ha entrado al proyecto además de la especificación misma.** Se adopta, con tres correcciones.

Y trae un dato que **cambia el plan**: revela que ya existe una implementación de 4 agentes en curso que nadie mencionó en el Decision Gate. Eso hay que resolverlo esta semana. Está en §1.4.

---

## 1.1 · Por qué la propuesta es buena

**Ataca el riesgo R-03 de frente, y lo hace mejor que la especificación.**

En §12.1 de la especificación registré esto:

> **R-03 — Adaptación cosmética:** los paquetes de distintos perfiles difieren en adjetivos pero no en profundidad real. Falla AC-06.1 y AC-19.3, y con ellos la casilla 4 del Checklist. **Impacto: Alto.**

Marely identificó **exactamente el mismo problema**, de forma independiente, y lo dice con más precisión que yo:

> *"Hoy el Redactor recibe la instrucción genérica 'adaptá al perfil X'. El LLM interpreta libremente qué significa eso… El contenido no varía realmente entre perfiles (solo cambia el tono)."*

La diferencia es que yo lo registré como riesgo y ella propone el **mecanismo concreto** para eliminarlo. Eso es más valioso.

**Los tres aportes reales:**

| Aporte | Por qué importa |
|---|---|
| **Convierte un criterio subjetivo en parámetros verificables** | AC-06.1 decía "los paquetes difieren de forma observable en vocabulario y profundidad" — imposible de testear automáticamente. Con nivel Bloom + andamiaje + registro explícitos, se puede **asertar sobre ellos en una prueba unitaria**. Un criterio de aceptación pasa de "se ve distinto" a "el nivel Bloom del paquete A es 2 y el del B es 5". |
| **Da una línea de pitch defendible** | *"Adaptación cognitiva sistemática, no sólo cambio de tono."* En un elevator pitch de 5 minutos frente a un jurado que ya vio diez proyectos que envuelven un LLM, **la Taxonomía de Bloom es la diferencia entre 'usamos IA' y 'sabemos de pedagogía'.** Eso es exactamente el sector del Hackathon: EdTech. |
| **Reduce la iteración de prompts, que es donde se va el tiempo** | Con parámetros explícitos no hay que descubrir por ensayo y error qué significa "adaptá a principiante". Se escribe una vez y se reutiliza. **Probablemente se paga sola en horas ahorradas.** |

**Además, encaja sin agregar alcance.** No es un requisito nuevo: es la especificación de *cómo* se implementa `FR-GEN-03` (adaptación de lenguaje, profundidad y tono al perfil), que ya era `MUST`. Ese es el mejor tipo de propuesta posible en un proyecto con el presupuesto apretado: **hace concreto lo que ya había que hacer, en vez de sumar cosas.**

Su §6 —la misma frase sobre el Scrum Master convertida en 4 salidas— es, además, **la mejor demo del proyecto**. Es instantáneamente legible para cualquier jurado, técnico o no.

---

## 1.2 · Las tres correcciones antes de adoptarla

### Corrección 1 — Desacoplarla de la arquitectura (importante)

La propuesta asume una arquitectura que **el equipo todavía no ha decidido**: menciona `supervisor.py`, `agente_investigador.py`, `agente_critico_revisor.py`, "el grafo" y `AgentState`. Eso es un sistema multi-agente con LangGraph.

Según el documento del Hackathon (p.6), el sistema multi-agente es un **diferencial opcional**, no un requisito. Y nuestro Decision Gate dejó la elección de framework de orquestación explícitamente para la fase 2.

**Corrección:** el módulo `pedagogia/` debe ser una **función pura**, sin dependencias del grafo ni del state:

```
build_pedagogical_spec(perfil: str, nivel_detalle: str) -> PedagogicalSpec
build_pedagogical_prompt_fragment(spec: PedagogicalSpec) -> str
```

Así funciona igual si el redactor es un agente en un grafo, un paso de una cadena, o una función suelta. **Y se puede construir esta semana, antes de decidir la arquitectura, sin riesgo de retrabajo.** Es la propuesta más valiosa y la única que puede empezar ya.

### Corrección 2 — Alinear `nivel_detalle` con el contrato

Su código pasa `nivel_detalle=3` (entero). El Decision Gate (§4, A-06) fijó tres valores de texto: `"Didactico"`, `"Estandar"`, `"Profundo"`.

**Corrección:** el módulo recibe el texto. Si internamente lo mapea a un entero, es asunto suyo, pero el contrato es el del gate.

### Corrección 3 — El choque entre Principiante y Gestor (la única debilidad real)

En su tabla de mapeo, dos perfiles quedan idénticos en dos de los tres ejes:

| Perfil | Bloom's | Andamiaje | Registro |
|---|---|---|---|
| Principiante / Transición | Entender (2) | Alto | Cotidiano |
| Gestor / Ejecutivo No Técnico | Entender (2) | Alto | **Ejecutivo** |

Sólo los distingue el registro. Pero si se miran **sus propios ejemplos** de §6, la diferencia real entre esas dos salidas no es lingüística: el texto del Principiante explica **qué es**, y el del Gestor explica **qué impacto tiene en el negocio**. Eso no es registro, es **foco**.

**Corrección propuesta — un cuarto eje, `foco`:**

| Perfil | Bloom's | Andamiaje | Registro | **Foco** |
|---|---|---|---|---|
| Principiante / Transición | Entender (2) | Alto | Cotidiano | **Comprensión conceptual** |
| Desarrollador Junior / Semi Senior | Aplicar (3) | Medio | Técnico | **Ejecución práctica** |
| Líder Técnico / Arquitecto | Evaluar (5) | Bajo | Técnico-estratégico | **Criterio de decisión** |
| Gestor / Ejecutivo No Técnico | Entender (2) | Alto | Ejecutivo | **Impacto en negocio** |

Con esto los 4 perfiles son distintos en al menos dos ejes, y el eje `foco` **conecta directamente con el esquema del formato TL;DR** que definimos en el Decision Gate (`punto_clave` → `implicacion` → `relevancia_negocio`). Las dos piezas se refuerzan.

---

## 1.3 · Qué cuesta y de dónde sale

| Concepto | Horas |
|---|---|
| Módulo `pedagogia/` (6 archivos, ~300 líneas) | 6-8 |
| Pruebas unitarias por eje | 2-3 |
| Integración en el redactor | 1 |
| Documentación en README con ejemplos | 1-2 |
| **Total** | **10-14 h** |

Contra un presupuesto que ya estaba 25-35% sobrecargado, esto es real y hay que pagarlo con algo.

**Recomendación: se paga con el Quiz.** Volver a 3 formatos (Flashcards + Tutorial + TL;DR) libera 8 h, y el módulo de pedagogía **aporta más a la evaluación y al pitch que un cuarto formato**. La casilla 4 del Checklist pide ≥2 formatos: con 3 sigue habiendo margen. Y la diferencia entre perfiles —que es lo que esa casilla mide de verdad— queda mucho más fuerte con Bloom que con un formato extra.

**Alternativa si quieren conservar el Quiz:** adelantar el punto de corte del 29 al **27 de septiembre**, y que el Quiz sea lo primero que cae.

---

## 1.4 · 🔴 Lo que hay que resolver esta semana

La propuesta menciona, como si ya existiera:

- Una estructura `agentes/` con `supervisor.py`, `agente_investigador.py`, `agente_redactor_pedagogico.py`, `agente_critico_revisor.py`
- Un grafo de decisión y un `AgentState`
- Y en su §11: *"Franklin, me gusta cómo armaste el flujo de 4 agentes"*

**Eso significa que alguien ya construyó un sistema multi-agente, y el Decision Gate no lo sabía.** Tres consecuencias:

1. **El Decision Gate puede estar decidiendo sobre una base desactualizada.** Clasificamos el multi-agente como `COULD` (opcional, p.6). Si ya está hecho, dejó de ser una decisión y pasó a ser un hecho — y probablemente un activo, no un problema.
2. **La estimación de presupuesto puede estar mal en ambas direcciones.** Si el flujo de 4 agentes ya funciona, sobran horas que yo conté. Si está a medias, falta trabajo que no conté.
3. **El agente crítico/revisor de Franklin y el verificador de fidelidad de D-02 son probablemente la misma pieza.** Si es así, se ahorran ~10 h. Si se construyen por separado, se duplica trabajo.

**Acción, antes del lunes:** que Franklin muestre qué hay construido y en qué estado. Con eso reviso el presupuesto de la §5 del Decision Gate y probablemente mejore. **No es una mala noticia — es información que faltaba.** Pero decidir con ella el 29 de septiembre en vez de hoy sí sería malo.

---

## 1.5 · Respuesta directa a la pregunta

> *¿Está muy escueta, hay algo que aporta, o seguimos con nuestro plan?*

**No está escueta, aporta bastante, y no compite con el plan: lo completa.**

Es la única propuesta hasta ahora que ataca el riesgo R-03, que era uno de los tres riesgos altos del proyecto. Se adopta con las tres correcciones de §1.2, se paga con el Quiz, y se le pide a Marely que **arranque ya** — es el único trabajo que no depende de la decisión de arquitectura.

Vale la pena decírselo así. Una propuesta que identifica sola un riesgo que estaba en la especificación, y que además trae el módulo ya armado, merece que se le diga que es buena.

---

# PARTE 2 · Configuración intercambiable de proveedor de LLM

## 2.1 · El concepto, en una idea

El código **nunca** nombra a Gemini, a Ollama ni a DeepSeek. El código pide *"dame el LLM"* y una sola función —la fábrica— decide cuál entregar, leyendo una variable de entorno.

```
CÓDIGO DE LA APLICACIÓN
         │
         │  get_llm()   ← nunca sabe qué proveedor hay detrás
         ▼
  ┌─────────────┐
  │   FÁBRICA   │ ← lee LLM_PROVIDER del entorno
  └──────┬──────┘
         │
    ┌────┴────┬─────────┬──────────┬─────────┐
    ▼         ▼         ▼          ▼         ▼
  Gemini   Ollama   DeepSeek   Anthropic   Kimi
```

Cambiar de proveedor = cambiar **una línea en un archivo `.env`**. Sin tocar código, sin recompilar, sin reabrir un archivo `.py`.

## 2.2 · La decisión que más plata les ahorra

**Separen el proveedor del LLM del proveedor de embeddings.** Esto es lo más importante de toda esta sección.

| | Cuántas llamadas por documento | Qué tan caro |
|---|---|---|
| **Embeddings** | **Una por chunk** — decenas o cientos | Barato por llamada, **brutal por volumen** |
| **LLM de generación** | 2 o 3 por paquete | Caro por llamada, **poco volumen** |

Si ponen los embeddings en el mismo proveedor de pago que el LLM, el volumen de chunks se come la cuota gratuita antes de que alcancen a iterar los prompts.

**Recomendación:** embeddings en **Ollama local** (gratis, ilimitado, sin cuota, sin red) y LLM de generación en Gemini gratuito. Con eso la cuota gratuita se gasta sólo en lo que de verdad necesita un modelo grande.

**Beneficio lateral para la demo:** con embeddings locales, la indexación no depende de internet. Una de las dos dependencias de red del pitch desaparece.

## 2.3 · Tres proveedores, no dos

En el Decision Gate quedó que hacía falta un plan B. En realidad hacen falta **tres papeles distintos**, y pueden ser proveedores distintos:

| Papel | Qué hace | Sugerencia |
|---|---|---|
| **Redactor** | Genera el contenido adaptado. Necesita el mejor modelo | Gemini gratuito → pago si se agota |
| **Verificador** (D-02) | Sólo clasifica afirmaciones como soportadas o no. **Tarea mucho más simple** | Puede ser un modelo más barato o local. **No desperdicien el modelo bueno acá** |
| **Embeddings** | Vectoriza chunks | Ollama local |

Por eso el `.env` de abajo tiene tres bloques separados.

## 2.4 · Los archivos

Les dejo tres archivos listos para el repositorio: `.env.example`, `config.py` y `llm_provider.py`. Están en la carpeta junto a este documento.

**Uso:**

```bash
cp .env.example .env     # .env es el real, con las claves; NUNCA se sube a Git
```

Y en el código, en cualquier parte:

```python
from config import settings
from llm_provider import get_llm, get_verifier_llm, get_embeddings

llm = get_llm()              # el que diga LLM_PROVIDER
verificador = get_verifier_llm()
embeddings = get_embeddings()
```

Para cambiar de proveedor, una línea:

```bash
LLM_PROVIDER=gemini      # →  LLM_PROVIDER=deepseek
```

## 2.5 · 🔴 Seguridad — esto es lo que más los puede hundir

El riesgo **R-07** de la especificación: credenciales versionadas en un repositorio público de GitHub. Con las claves de OCI **y** de varios LLM en el mismo proyecto, y 3 personas haciendo commits con prisa la última semana, la probabilidad no es baja.

**Tres medidas, las tres obligatorias:**

**1 · `.gitignore` — antes del primer commit**

```gitignore
.env
.env.local
*.pem
~/.oci/
oci_api_key*.pem
```

**2 · `.env.example` se versiona, `.env` no.** El ejemplo lleva los nombres de las variables con valores vacíos. El real, con las claves, sólo vive en cada máquina.

**3 · Una verificación antes de entregar:**

```bash
git log --all --full-history -- .env
```

Si eso devuelve algo, **una clave quedó en el historial** y borrar el archivo no la elimina. Hay que rotar la clave.

> Si una clave se filtra: rotarla en el proveedor. No basta con borrar el archivo — el historial de Git la conserva.

## 2.6 · Fallback manual, no automático

Tentación natural: que si el proveedor principal falla, el sistema pase solo al siguiente.

**No lo hagan, no en 14 días.** Un fallback automático esconde el problema: el sistema "funciona" mientras consume cuota de pago sin que nadie se entere, y la causa del fallo queda enterrada.

**Lo correcto:** que falle rápido y con un mensaje que diga **cuál** proveedor falló y **por qué**. Cambiar de proveedor es una decisión humana de un segundo. Ese comportamiento ya está en el `llm_provider.py` que les dejo.

## 2.7 · Una advertencia honesta sobre los modelos que nombraron

Mencionaron DeepSeek v4, Claude Opus 4.6 y Kimi K3. **No puedo confirmarles los identificadores exactos de esos modelos, ni sus condiciones de capa gratuita al día de hoy** — mi conocimiento tiene fecha de corte y los catálogos de modelos cambian cada pocas semanas.

Por eso el diseño de arriba importa: **los identificadores van en el `.env`, no en el código.** Si un nombre de modelo está mal, cuesta corregirlo una línea.

**Acción:** quien configure cada proveedor verifica en la documentación oficial, el día que lo configure, el identificador exacto del modelo y los límites de la capa gratuita. Y lo anota en el README.

---

## 2.8 · Nota sobre la cuenta OCI

Confirmaron que el trial ya venció. **Esa es la mejor noticia operativa del proyecto**, aunque no lo parezca:

- La cuenta ya es **Always Free pura**: **20 GB** de Object Storage combinados entre todos los tiers, y **50.000 solicitudes API al mes**.
- Los recursos Always Free **no expiran**. No hay reloj corriendo contra la entrega del 2 de octubre.
- **No hay riesgo de cobro accidental**, que era el temor del programa ONE.

Para lo que van a usar (PDFs y JSONs de unos pocos KB, y 2 cargas por generación) esos límites son holgados. Con 3 personas probando intensamente dos semanas, ni se acercan a las 50.000 solicitudes.

**Dos cosas por verificar de todos modos:**

1. **Que el bucket esté en la home region de la cuenta.** Always Free sólo aplica ahí. Si alguien lo creó en otra región durante el trial, hay que recrearlo.
2. **Que la cuenta se use al menos una vez cada 60 días.** Las cuentas gratuitas inactivas se desactivan. Con ustedes trabajando a diario, no es problema — pero conviene saberlo si el proyecto se retoma después del Hackathon.

---

## Resumen de acciones

| # | Acción | Quién | Cuándo |
|---|---|---|---|
| 1 | **Franklin muestra qué hay construido del flujo de 4 agentes** | Franklin | Antes del lunes |
| 2 | Decirle a Marely que la propuesta se adopta, con las 3 correcciones de §1.2 | — | Hoy |
| 3 | Marely arranca el módulo `pedagogia/` como función pura | Marely | Ya |
| 4 | Decidir: ¿el Quiz se cae para pagar el módulo de pedagogía? | Equipo | 22 sept |
| 5 | Crear `.gitignore` con `.env` **antes del primer commit** | — | Antes del primer commit |
| 6 | Verificar que el bucket esté en la home region | — | 19 sept |
| 7 | Instalar Ollama y elegir modelo de embeddings local | — | 22 sept |
| 8 | Verificar identificadores y límites reales de cada proveedor, y anotarlos en el README | — | Al configurar cada uno |
