"""
NuevaMente — Calibración con e5 real: umbral de recuperación y bandas de fidelidad.

Mide, con los embeddings reales y las guías indexadas:

  1. Recuperación: el mejor puntaje de cada consulta contra los chunks de su
     guía, separando consultas del tema, de un tema vecino y ajenas.
  2. Fidelidad: el mejor coseno de cada afirmación (con prefijo "query: ", como
     la verificará fidelidad/) contra los chunks de su guía, separando
     ancladas, inventadas del tema e inventadas ajenas.

No decide nada: deja los datos, compara con los valores de hoy y sugiere con
reglas a la vista (src/rag/calibracion.py). Las bandas se fijan el 06/10 con
calibrar_bandas() de fidelidad/.

Uso, desde la raíz del repo y con el .venv activo:

    python scripts/calibrar_e5.py --datos RUTA/calibracion.json --insumos ../../04_insumos --salida CARPETA

    --simular   sin red ni token: embeddings de bolsa de palabras y un índice
                temporal. Sirve para revisar el flujo; los números no son de e5.

Gasto con e5: indexa las guías que falten (las ya indexadas se reutilizan) y
embebe cada consulta y cada afirmación una vez, en lotes.
"""

from __future__ import annotations

import argparse
import dataclasses
import fnmatch
import hashlib
import json
import logging
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from langchain_core.embeddings import Embeddings

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.rag import calibracion as cal  # noqa: E402
from src.rag.configuracion import cargar_config  # noqa: E402
from src.rag.embeddings import EmbeddingsE5  # noqa: E402
from src.rag.errores import ErrorRAG  # noqa: E402
from src.rag.indexacion import indexar_archivo  # noqa: E402
from src.rag.vectorstore import AlmacenChroma  # noqa: E402

TIPOS_CONSULTA = ("tema", "vecina", "ajena")
TIPOS_AFIRMACION = ("anclada", "inventada_tema", "inventada_ajena")


def bandas_actuales() -> tuple[float, float]:
    """Bandas de hoy (CONTEXTO §6.8): las del .env si están, si no 0.55 y 0.85."""

    def leer(nombre: str, defecto: float) -> float:
        valor = (os.getenv(nombre) or "").strip().replace(",", ".")
        return float(valor) if valor else defecto

    return leer("FIDELIDAD_BANDA_BAJA", 0.55), leer("FIDELIDAD_BANDA_ALTA", 0.85)


class EmbeddingsSimulados(Embeddings):
    """Bolsa de palabras con hashing, sin red: solo para revisar el flujo."""

    def __init__(self, dimension: int) -> None:
        self.dimension = dimension

    def _vector(self, texto: str) -> list[float]:
        v = np.zeros(self.dimension)
        for palabra in re.findall(r"\w+", texto.lower()):
            v[int(hashlib.md5(palabra.encode("utf-8")).hexdigest()[:8], 16) % self.dimension] += 1.0
        norma = np.linalg.norm(v)
        return (v / norma if norma else np.eye(1, self.dimension)[0]).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def embeder_consultas(self, textos: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in textos]


# =============================================================================
# Datos
# =============================================================================


def cargar_datos(ruta: Path) -> dict[str, Any]:
    """Lee y valida el archivo de consultas y afirmaciones."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    guias = datos.get("guias") or {}
    problemas = []
    for campo, tipos in (("consultas", TIPOS_CONSULTA), ("afirmaciones", TIPOS_AFIRMACION)):
        for i, item in enumerate(datos.get(campo) or []):
            if item.get("guia") not in guias:
                problemas.append(f"{campo}[{i}]: guía {item.get('guia')!r} no está en 'guias'")
            if item.get("tipo") not in tipos:
                problemas.append(f"{campo}[{i}]: tipo {item.get('tipo')!r}; se esperaba uno de {tipos}")
            if not str(item.get("texto") or "").strip():
                problemas.append(f"{campo}[{i}]: texto vacío")
    if problemas:
        raise ValueError("El archivo de calibración tiene problemas:\n  - " + "\n  - ".join(problemas))
    return datos


def ubicar_guias(guias: dict[str, str], carpeta: Path) -> dict[str, Path]:
    """Encuentra el PDF de cada guía por patrón (los nombres traen la «í» descompuesta)."""
    archivos = [p for p in carpeta.iterdir() if p.is_file()]
    rutas = {}
    for clave, patron in guias.items():
        coincidencias = [p for p in archivos if fnmatch.fnmatch(p.name, patron)]
        if len(coincidencias) != 1:
            raise ValueError(f"La guía {clave!r} ({patron}) coincide con {len(coincidencias)} archivos en {carpeta}")
        rutas[clave] = coincidencias[0]
    return rutas


# =============================================================================
# Medición
# =============================================================================


def medir(items: list[dict[str, Any]], document_ids: dict[str, str], embeddings: Any, almacen: AlmacenChroma) -> None:
    """Agrega a cada ítem su mejor coseno contra los chunks de su guía (en lotes por guía)."""
    for guia, document_id in document_ids.items():
        de_la_guia = [item for item in items if item["guia"] == guia]
        if not de_la_guia:
            continue
        vectores = embeddings.embeder_consultas([item["texto"] for item in de_la_guia])
        for item, vector in zip(de_la_guia, vectores, strict=True):
            mejor = almacen.consultar(document_id, vector, top_k=1)[0]
            item["puntaje"] = round(mejor.score, 4)
            item["chunk"] = mejor.chunk_id
            item["pagina_chunk"] = mejor.metadatos.get("pagina")


def puntajes(items: list[dict[str, Any]], *tipos: str) -> list[float]:
    return [item["puntaje"] for item in items if item["tipo"] in tipos]


def analizar(
    consultas: list[dict[str, Any]],
    afirmaciones: list[dict[str, Any]],
    umbral_actual: float,
    bandas_de_hoy: tuple[float, float],
) -> dict:
    banda_baja, banda_alta = bandas_de_hoy
    tema, vecinas, ajenas = (puntajes(consultas, t) for t in TIPOS_CONSULTA)
    ancladas = puntajes(afirmaciones, "anclada")
    inventadas = puntajes(afirmaciones, "inventada_tema", "inventada_ajena")

    resultado: dict[str, Any] = {"recuperacion": {}, "fidelidad": {}}
    rec = resultado["recuperacion"]
    por_tipo = zip(TIPOS_CONSULTA, (tema, vecinas, ajenas), strict=True)
    rec["resumen"] = {tipo: cal.resumir(valores).como_dict() for tipo, valores in por_tipo if valores}
    if tema and ajenas:
        rec["umbral_actual"] = {"umbral": umbral_actual, **cal.contar_errores_umbral(umbral_actual, tema, ajenas)}
        rec["sugerido"] = cal.sugerir_umbral(tema, ajenas)
        if vecinas:
            rec["vecinas_sobre_umbral_actual"] = sum(v >= umbral_actual for v in vecinas)
            rec["vecinas_sobre_umbral_sugerido"] = sum(v >= rec["sugerido"]["umbral"] for v in vecinas)

    fid = resultado["fidelidad"]
    fid["resumen"] = {
        t: cal.resumir(puntajes(afirmaciones, t)).como_dict() for t in TIPOS_AFIRMACION if puntajes(afirmaciones, t)
    }
    if ancladas and inventadas:
        sugeridas = cal.sugerir_bandas(ancladas, inventadas)
        fid["bandas_sugeridas"] = sugeridas
        fid["efecto_bandas_actuales"] = cal.efecto_de_bandas(ancladas, inventadas, banda_baja, banda_alta)
        fid["efecto_bandas_sugeridas"] = cal.efecto_de_bandas(
            ancladas, inventadas, sugeridas["baja"], sugeridas["alta"]
        )
        fid["puntaje_sin_juez"] = {}
        for tipo in TIPOS_AFIRMACION:
            valores = puntajes(afirmaciones, tipo)
            if valores:
                fid["puntaje_sin_juez"][tipo] = {
                    "hoy": cal.puntaje_sin_juez(valores, banda_baja, banda_alta, reescalado=False),
                    "propuesta": cal.puntaje_sin_juez(
                        valores, sugeridas["baja"], sugeridas["alta"], reescalado=True
                    ),
                }
    return resultado


# =============================================================================
# Informe
# =============================================================================


def _tabla_resumen(resumen: dict[str, dict]) -> list[str]:
    lineas = ["| Tipo | n | Mín | p10 | Mediana | p90 | Máx |", "|---|---|---|---|---|---|---|"]
    for tipo, r in resumen.items():
        celdas = [tipo, r["n"], r["minimo"], r["p10"], r["mediana"], r["p90"], r["maximo"]]
        lineas.append("| " + " | ".join(str(c) for c in celdas) + " |")
    return lineas


def _tabla_efecto(nombre: str, efecto: dict) -> str:
    return (
        f"| {nombre} ({efecto['baja']} / {efecto['alta']}) | {efecto['inventadas_aprobadas_sin_juez']} | "
        f"{efecto['ancladas_rechazadas_sin_juez']} | {efecto['llamadas_al_juez']} ({efecto['fraccion_al_juez']:.0%}) |"
    )


def a_markdown(informe: dict[str, Any]) -> str:
    rec, fid = informe["analisis"]["recuperacion"], informe["analisis"]["fidelidad"]
    lineas = [
        f"# Calibración con e5 ({informe['etiqueta']}, {informe['fecha']})",
        "",
        "**SIMULADO: puntajes de bolsa de palabras, no de e5.**" if informe["simulado"] else "",
        f"- Datos: `{informe['datos']}` · {len(informe['consultas'])} consultas · "
        f"{len(informe['afirmaciones'])} afirmaciones",
        "- Guías: " + " · ".join(f"{g} ({d['chunks']} chunks{', reusada' if d['reusada'] else ''})"
                                  for g, d in informe["guias"].items()),
        "",
        "## 1. Umbral de recuperación",
        "",
        *_tabla_resumen(rec.get("resumen", {})),
        "",
    ]
    if "sugerido" in rec:
        actual, sugerido = rec["umbral_actual"], rec["sugerido"]
        lineas += [
            f"- Hoy ({actual['umbral']}): {actual['errores_tema']} consultas del tema quedarían afuera y "
            f"{actual['errores_ajenas']} ajenas pasarían.",
            f"- Sugerido: **{sugerido['umbral']}** ({'separa' if sugerido['separa'] else 'no separa del todo'}; "
            f"margen {sugerido['margen']}): {sugerido['errores_tema']} del tema afuera, "
            f"{sugerido['errores_ajenas']} ajenas adentro.",
        ]
        if "vecinas_sobre_umbral_actual" in rec:
            lineas.append(
                f"- Vecinas que pasan: {rec['vecinas_sobre_umbral_actual']} con el umbral de hoy y "
                f"{rec['vecinas_sobre_umbral_sugerido']} con el sugerido."
            )
    lineas += ["", "## 2. Bandas de fidelidad", "", *_tabla_resumen(fid.get("resumen", {})), ""]
    if "bandas_sugeridas" in fid:
        sugeridas = fid["bandas_sugeridas"]
        lineas += [
            f"Sugeridas: baja **{sugeridas['baja']}**, alta **{sugeridas['alta']}** "
            f"({'ancladas e inventadas se separan' if sugeridas['separa'] else 'ancladas e inventadas se solapan'}; "
            f"margen {sugeridas['margen']}).",
            "",
            "| Bandas (baja / alta) | Inventadas aprobadas sin juez | Ancladas rechazadas sin juez | Al juez |",
            "|---|---|---|---|",
            _tabla_efecto("Hoy", fid["efecto_bandas_actuales"]),
            _tabla_efecto("Sugeridas", fid["efecto_bandas_sugeridas"]),
            "",
            "Puntaje medio sin juez (modo desarrollo): hoy, con el coseno crudo en la zona dudosa; "
            "propuesta, con el coseno reescalado.",
            "",
            "| Tipo | Hoy | Propuesta |",
            "|---|---|---|",
            *[f"| {tipo} | {v['hoy']} | {v['propuesta']} |" for tipo, v in fid["puntaje_sin_juez"].items()],
        ]
    lineas += ["", "## 3. Casos a mirar", ""]
    for titulo, items in (
        ("Afirmaciones ancladas con menor puntaje", sorted(
            (a for a in informe["afirmaciones"] if a["tipo"] == "anclada"), key=lambda a: a["puntaje"])[:5]),
        ("Afirmaciones inventadas con mayor puntaje", sorted(
            (a for a in informe["afirmaciones"] if a["tipo"] != "anclada"), key=lambda a: -a["puntaje"])[:5]),
        ("Consultas ajenas con mayor puntaje", sorted(
            (c for c in informe["consultas"] if c["tipo"] == "ajena"), key=lambda c: -c["puntaje"])[:3]),
    ):
        lineas.append(f"**{titulo}**")
        lineas += [f"- {i['puntaje']} · {i['guia']} · {i['tipo']} · «{i['texto']}»" for i in items]
        lineas.append("")
    return "\n".join(lineas) + "\n"


# =============================================================================
# Programa
# =============================================================================


def main(argumentos: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.WARNING, format="  aviso: %(message)s")
    logging.getLogger("pypdf").setLevel(logging.ERROR)  # PDFs con referencias rotas: ruido sin efecto

    parser = argparse.ArgumentParser(description="Calibración con e5: umbral de recuperación y bandas de fidelidad.")
    parser.add_argument("--datos", required=True, type=Path, help="JSON de consultas y afirmaciones.")
    parser.add_argument("--insumos", required=True, type=Path, help="Carpeta con los PDF de las guías.")
    parser.add_argument("--salida", type=Path, help="Carpeta donde guardar el JSON y el Markdown.")
    parser.add_argument("--etiqueta", default="local")
    parser.add_argument("--simular", action="store_true", help="Sin red ni token (índice temporal).")
    args = parser.parse_args(argumentos)

    try:
        datos = cargar_datos(args.datos)
        rutas = ubicar_guias(datos["guias"], args.insumos)
    except (OSError, ValueError) as err:
        print(f"No se puede empezar: {err}")
        return 2

    config = cargar_config()  # también carga el .env, de donde salen las bandas de hoy
    bandas_de_hoy = bandas_actuales()
    if args.simular:
        config = dataclasses.replace(config, chroma_path=Path(tempfile.mkdtemp(prefix="chroma_simulado_")))
        embeddings: Any = EmbeddingsSimulados(config.dimension_embeddings)
        print("MODO SIMULADO: sin red ni token; los números no son de e5.")
    else:
        embeddings = EmbeddingsE5(config)
    almacen = AlmacenChroma(config)
    print(f"Configuración: {config.resumen_seguro()}")

    consultas = [dict(c) for c in datos.get("consultas", [])]
    afirmaciones = [dict(a) for a in datos.get("afirmaciones", [])]
    usadas = {item["guia"] for item in consultas + afirmaciones}

    try:
        guias: dict[str, dict[str, Any]] = {}
        for clave in sorted(usadas):
            ya_estaba = None
            print(f"Indexando {clave}...")
            textos_antes = embeddings.estadisticas.textos if isinstance(embeddings, EmbeddingsE5) else 0
            document_id, cantidad = indexar_archivo(rutas[clave], embeddings=embeddings, almacen=almacen)
            if isinstance(embeddings, EmbeddingsE5):
                ya_estaba = embeddings.estadisticas.textos == textos_antes
            guias[clave] = {"archivo": rutas[clave].name, "document_id": document_id, "chunks": cantidad,
                            "reusada": bool(ya_estaba)}
        print("Midiendo consultas y afirmaciones...")
        document_ids = {clave: d["document_id"] for clave, d in guias.items()}
        medir(consultas, document_ids, embeddings, almacen)
        medir(afirmaciones, document_ids, embeddings, almacen)
    except ErrorRAG as err:
        print(f"Falló: {err}")
        return 1

    informe: dict[str, Any] = {
        "fecha": datetime.now().astimezone().isoformat(timespec="seconds"),
        "etiqueta": args.etiqueta,
        "simulado": args.simular,
        "datos": args.datos.name,
        "config": {
            "modelo": config.modelo_embeddings,
            "umbral_retrieval": config.umbral_retrieval,
            "banda_baja_actual": bandas_de_hoy[0],
            "banda_alta_actual": bandas_de_hoy[1],
            "chunk_size": config.chunk_size,
            "chunk_overlap": config.chunk_overlap,
            "chunk_minimo": config.chunk_minimo,
        },
        "guias": guias,
        "consultas": consultas,
        "afirmaciones": afirmaciones,
        "analisis": analizar(consultas, afirmaciones, config.umbral_retrieval, bandas_de_hoy),
    }
    if isinstance(embeddings, EmbeddingsE5):
        informe["consumo"] = embeddings.estadisticas.como_dict()

    resumen = a_markdown(informe)
    print()
    print(resumen)
    if args.salida:
        args.salida.mkdir(parents=True, exist_ok=True)
        base = f"calibracion_e5_{args.etiqueta}_{datetime.now():%Y%m%d-%H%M%S}"
        (args.salida / f"{base}.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.salida / f"{base}.md").write_text(resumen, encoding="utf-8")
        print(f"Guardado: {base}.json y {base}.md en {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
