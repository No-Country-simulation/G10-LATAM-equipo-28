#!/usr/bin/env python3
"""
NuevaMente — Verificador de entorno.

Cada persona del equipo corre esto ANTES de escribir su primera linea de codigo:

    python verificar_entorno.py

Dice exactamente que falta en TU maquina y como arreglarlo. No modifica nada.

El objetivo es que nadie pierda medio dia del 22 de septiembre descubriendo que
le faltaba un paquete. Si los tres corren esto y sale todo verde, el equipo
arranca parejo.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

VERDE, ROJO, AMARILLO, GRIS, FIN = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"
if os.name == "nt" and not os.environ.get("WT_SESSION"):
    VERDE = ROJO = AMARILLO = GRIS = FIN = ""  # consola vieja de Windows

OK, FALLA, AVISO = f"{VERDE}[ OK ]{FIN}", f"{ROJO}[FALTA]{FIN}", f"{AMARILLO}[AVISO]{FIN}"

resultados: list[tuple[str, bool, str]] = []


def revisar(nombre: str, condicion: bool, arreglo: str = "", critico: bool = True) -> bool:
    etiqueta = OK if condicion else (FALLA if critico else AVISO)
    print(f"  {etiqueta}  {nombre}")
    if not condicion and arreglo:
        for linea in arreglo.strip().split("\n"):
            print(f"         {GRIS}{linea}{FIN}")
    resultados.append((nombre, condicion, "critico" if critico else "opcional"))
    return condicion


def hay_paquete(modulo: str) -> bool:
    return importlib.util.find_spec(modulo) is not None


def seccion(titulo: str) -> None:
    print(f"\n{titulo}")
    print("  " + "-" * (len(titulo) + 2))


# =============================================================================

print("\n" + "=" * 62)
print("  NuevaMente — verificacion de entorno")
print("=" * 62)

# --- 1. Python -----------------------------------------------------------
seccion("1. Python")

v = sys.version_info
revisar(
    f"Python 3.11 o superior (tenes {v.major}.{v.minor}.{v.micro})",
    v >= (3, 11),
    "Instalar Python 3.11+ desde python.org o con pyenv.",
)

en_venv = sys.prefix != sys.base_prefix
revisar(
    "Entorno virtual activo",
    en_venv,
    "python -m venv .venv\n"
    "Windows:  .venv\\Scripts\\activate\n"
    "Linux/Mac: source .venv/bin/activate",
    critico=False,
)

# --- 2. Dependencias -----------------------------------------------------
seccion("2. Dependencias de Python")

for modulo, etiqueta, critico in [
    ("pydantic", "pydantic (contratos tipados)", True),
    ("dotenv", "python-dotenv (lee el .env)", True),
    ("pytest", "pytest (pruebas)", True),
    ("langchain", "langchain", True),
    ("langgraph", "langgraph (orquestacion)", True),
    ("chromadb", "chromadb (vector store)", True),
    ("pypdf", "pypdf (extraccion de PDF)", True),
    ("streamlit", "streamlit (interfaz)", True),
    ("oci", "oci (Object Storage, OBLIGATORIO del Hackathon)", True),
    ("langchain_ollama", "langchain-ollama (embeddings locales)", True),
    ("langchain_google_genai", "langchain-google-genai (Gemini)", False),
]:
    revisar(etiqueta, hay_paquete(modulo), "pip install -r requirements.txt", critico)

# --- 3. Ollama -----------------------------------------------------------
seccion("3. Ollama — embeddings locales")

ollama = shutil.which("ollama")
if revisar(
    "Ollama instalado",
    ollama is not None,
    "Descargar de https://ollama.com/download\n"
    "Es lo que evita gastar la cuota gratuita de Gemini vectorizando chunks.",
):
    try:
        salida = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=10
        ).stdout
        revisar(
            "Servicio de Ollama respondiendo",
            "NAME" in salida or salida.strip() != "",
            "Abrir la aplicacion Ollama, o correr:  ollama serve",
        )
        revisar(
            "Modelo de embeddings descargado (nomic-embed-text)",
            "nomic-embed-text" in salida,
            "ollama pull nomic-embed-text",
        )
    except Exception:
        revisar("Servicio de Ollama respondiendo", False, "Abrir Ollama, o: ollama serve")

# --- 4. Configuracion ----------------------------------------------------
seccion("4. Configuracion del proyecto")

raiz = Path(__file__).resolve().parent
env = raiz / ".env"
revisar(
    "Archivo .env creado",
    env.exists(),
    "cp .env.example .env     (Windows:  copy .env.example .env)\n"
    "Y despues llenar las claves.",
)

gitignore = raiz / ".gitignore"
tiene_env = gitignore.exists() and ".env" in gitignore.read_text(encoding="utf-8")
revisar(
    "🔴 .gitignore protege el .env  (riesgo R-07)",
    tiene_env,
    "Agregar la linea  .env  al .gitignore ANTES del primer commit.\n"
    "Una clave subida a GitHub no se borra con git rm: queda en el historial.",
)

if env.exists():
    contenido = env.read_text(encoding="utf-8")

    def tiene_valor(clave: str) -> bool:
        for linea in contenido.splitlines():
            if linea.strip().startswith(f"{clave}=") and linea.split("=", 1)[1].strip():
                return True
        return False

    revisar(
        "GEMINI_API_KEY con valor",
        tiene_valor("GEMINI_API_KEY"),
        "Sacar una clave en https://aistudio.google.com/apikey\n"
        "Cada persona usa la SUYA: asi no comparten cuota gratuita.",
    )
    revisar("OCI_BUCKET_NAME con valor", tiene_valor("OCI_BUCKET_NAME"), "Lo define el equipo.")
    revisar(
        "OCI_NAMESPACE con valor",
        tiene_valor("OCI_NAMESPACE"),
        "Obtenerlo con:  oci os ns get",
    )

# --- 5. OCI --------------------------------------------------------------
seccion("5. Oracle Cloud — requisito OBLIGATORIO del Hackathon")

oci_config = Path.home() / ".oci" / "config"
revisar(
    "Archivo ~/.oci/config presente",
    oci_config.exists(),
    "Consola de OCI > Perfil > My profile > API keys > Add API key.\n"
    "Descargar la llave privada y pegar el bloque de configuracion en ~/.oci/config",
)
if oci_config.exists():
    texto = oci_config.read_text(encoding="utf-8", errors="ignore")
    revisar("La configuracion declara una region", "region" in texto, "")
    revisar(
        "La llave privada referenciada existe",
        any(
            Path(l.split("=", 1)[1].strip()).expanduser().exists()
            for l in texto.splitlines()
            if l.strip().startswith("key_file")
        ),
        "Revisar la ruta de key_file en ~/.oci/config",
    )

# --- 6. Git --------------------------------------------------------------
seccion("6. Git")

revisar("Git instalado", shutil.which("git") is not None, "https://git-scm.com/downloads")
try:
    nombre = subprocess.run(
        ["git", "config", "user.name"], capture_output=True, text=True, timeout=5
    ).stdout.strip()
    revisar(
        "git user.name configurado",
        bool(nombre),
        'git config --global user.name "Tu Nombre"\n'
        "Hace falta para la casilla 8: commits claros y colaborativos.",
    )
except Exception:
    pass

# --- 7. Contratos --------------------------------------------------------
seccion("7. Contratos del proyecto")

contratos = raiz / "src" / "contracts" / "__init__.py"
if revisar("Modulo src/contracts presente", contratos.exists(), "Copiar la carpeta src/ del equipo."):
    try:
        sys.path.insert(0, str(raiz))
        from src.contracts import PerfilDestinatario  # noqa: F401

        revisar("Los contratos importan sin error", True)
    except Exception as exc:
        revisar("Los contratos importan sin error", False, f"{exc}")

# =============================================================================

print("\n" + "=" * 62)
criticos_mal = [n for n, ok, tipo in resultados if not ok and tipo == "critico"]
opcionales_mal = [n for n, ok, tipo in resultados if not ok and tipo == "opcional"]
total_ok = sum(1 for _, ok, _ in resultados if ok)

print(f"  {total_ok} de {len(resultados)} verificaciones en verde")

if criticos_mal:
    print(f"\n  {ROJO}Faltan {len(criticos_mal)} cosas criticas:{FIN}")
    for n in criticos_mal:
        print(f"    · {n}")
    print("\n  Arreglalas antes de empezar a programar.")
elif opcionales_mal:
    print(f"\n  {AMARILLO}Todo lo critico esta listo.{FIN} Pendientes opcionales:")
    for n in opcionales_mal:
        print(f"    · {n}")
else:
    print(f"\n  {VERDE}Entorno completo. Podes empezar.{FIN}")

print("=" * 62 + "\n")
sys.exit(1 if criticos_mal else 0)
