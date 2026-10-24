# Seguridad y datos — NuevaMente

> **Qué es este documento.** Qué información toca el sistema, dónde vive, qué controles hay
> implementados y qué riesgos quedan abiertos. Es el resumen de una página; el detalle de la
> auditoría está en [`seguridad_sprint3.md`](seguridad_sprint3.md).
>
> **Referencia:** `main` @ `346f631` (tag `v1.0.1`). Fecha: 2026-10-24.

## 1. Qué se guarda y dónde

| Dato | Dónde vive | Persistencia |
|---|---|---|
| Documento original (PDF/MD/TXT) | OCI Object Storage, prefijo `fuentes/` | Permanente, en el bucket |
| Paquete educativo (JSON validado) | OCI, prefijo `generados/` | Permanente |
| Salidas formateadas (PDF, Markdown) | OCI, prefijo `generados/formateados/` | Permanente |
| Vectores de los chunks | `chroma_db/` en disco local | Por máquina; fuera de Git |
| Estado de la corrida | `session_state` de Streamlit | Se pierde al recargar |
| Claves y tokens | `.env` en local / *Secrets* en la nube | Nunca en el repositorio |

**No se guardan datos personales de los usuarios**: no hay cuentas reales ni perfiles persistidos
(ver `docs/limitaciones-y-alcance.md`, puntos 2 y 7). El "perfil del destinatario" es un parámetro
de la solicitud, no un registro.

## 2. Secretos

Nunca se versionan (`.gitignore`): `.env`, `.env.local`, `*.pem`, `oci_api_key*`, `.oci/`,
`.streamlit/secrets.toml`, `chroma_db/`, `data/vector_store/`, `data/uploads/`, `checkpoints.sqlite*`.

Regla dura: **una clave que entra a un commit ya está comprometida**, aunque se borre después —
queda en el historial. Si pasa, se rota la clave; no se "arregla" con otro commit.

> Detalle menor: `.env` está listado dos veces en `.gitignore` (primera línea y casi al final). Es
> inofensivo, pero conviene dejarlo una sola vez.

## 3. Controles implementados

**Antes de cualquier llamada al LLM** (`src/grafo.py:265`, `src/seguridad/validadores.py`):

- Tema ≤ 1.000 caracteres, mensaje ≤ 12.000, instrucción de modificación ≤ 2.000.
- Detección de instrucción directa en el texto del usuario.
- Documento ≤ `MAX_DOCUMENT_SIZE_MB` (10 MB por defecto).
- La salida del Supervisor se valida contra el contrato antes de llegar al Investigador.

**Permisos por etapa** (`src/seguridad/permisos.py`): los cinco agentes **no reciben herramientas**;
`obtener_herramienta_autorizada` lanza `AccesoHerramientaDenegado` si la etapa no tiene permiso.
Los agentes solo tienen generador de texto estructurado.

**Acceso al bucket** (`src/seguridad/validadores.py:277`): las lecturas se limitan al prefijo
`fuentes/` y se rechazan segmentos `.`, `..` y barras invertidas. Ningún agente toca OCI: solo los
nodos determinísticos, vía servidor MCP.

**Red** (`src/seguridad/guardia_red.py`): allowlist de hosts (`api.groq.com`,
`generativelanguage.googleapis.com`, `api.deepseek.com`, `api.moonshot.cn`, `api.anthropic.com`),
bloqueo de IPs privadas y validación de redirecciones. La excepción de *loopback* existe solo para
Ollama local, en el puerto permitido.

**Costo** (`src/seguridad/rate_limiter.py`): ventana por modelo con estimación de tokens, y cascada
con fallback por cupo real. Sin fallback entre proveedores distintos, a propósito.

**Contrato** (`src/contracts/`): `extra="forbid"` en todos los modelos y `status` que no puede
mentir — si OCI falla o la fidelidad queda baja, el paquete sale como `exito_con_advertencias`.

## 4. Riesgos residuales (declarados, no ocultos)

1. **No hay autenticación real.** `src/arranque_demo.py` provee un login de demostración y cuotas
   simuladas. Ver `docs/limitaciones-y-alcance.md`, punto 2.
2. **ChromaDB 1.5.9 con advisories abiertos.** `pip-audit` reporta cuatro avisos únicos, uno de
   ellos RCE pre-autenticación (CVSS 9.3) **si el endpoint está expuesto y `trust_remote_code=true`**.
   En la configuración actual (`chromadb.PersistentClient`, `src/rag/vectorstore.py:76`) no hay
   endpoint de red, no se activa `trust_remote_code` y los vectores se calculan fuera de Chroma: las
   dos condiciones del aviso **no se cumplen**. El riesgo es latente, no activo — y hay que
   revisarlo antes de mover el índice a un servidor o de habilitar colecciones multi-inquilino.
3. **IAM por prefijo sin verificar en la cuenta.** La restricción de lecturas a `fuentes/` es de
   aplicación, no de IAM. Falta comprobar en la consola que el usuario/Instance Principal no pueda
   leer ni escribir fuera de los prefijos previstos (`seguridad_sprint3.md`, §"Riesgos residuales").
4. **Sin cifrado propio.** Se delega en OCI (en reposo) y en TLS (en tránsito). No hay cifrado de
   aplicación sobre el contenido de los documentos.
5. **Logs.** Están pensados para no incluir secretos, pero cualquier log que se comparta fuera del
   equipo debe revisarse antes: puede contener fragmentos del documento fuente.

## 5. Cómo verificar este documento

```bash
git grep -n "MAX_LONGITUD_\|MAX_DOCUMENT_SIZE_MB" -- src/seguridad/validadores.py
git grep -n "ETAPAS_AGENTE_SIN_HERRAMIENTAS\|AccesoHerramientaDenegado" -- src/seguridad/permisos.py
git grep -n "startswith(\"fuentes/\")" -- src/seguridad/validadores.py
git grep -n "api.groq.com\|trust_remote_code\|PersistentClient" -- src/
git check-ignore -v .env oci_api_key.pem chroma_db/x
```
