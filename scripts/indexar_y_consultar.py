"""
NuevaMente — Criterio de salida de T2-05: indexar una guía y consultarla.

Indexa un documento (si ya estaba indexado con la misma configuración, no
gasta cuota) y muestra lo que devuelve recuperar() para la consulta: chunk,
página y puntaje, marcando cuáles superan UMBRAL_RETRIEVAL.

Uso, desde la raíz del repo y con el .venv activo:

    python scripts/indexar_y_consultar.py --documento "RUTA/guía.pdf" --consulta "Scrum Master"

    --forzar           reindexa aunque ya esté indexado
    --salida CARPETA   guarda un JSON y un Markdown con el resultado
    --simular          sin red ni token: embeddings de bolsa de palabras y un
                       índice temporal. Sirve para revisar el flujo; los
                       puntajes no son los de e5.

Criterio del plan: la consulta «Scrum Master» devuelve chunks sobre
UMBRAL_RETRIEVAL (0.78 en el plan; 0.82 provisional desde T2-06).
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from langchain_core.embeddings import Embeddings

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.rag.configuracion import cargar_config  # noqa: E402
from src.rag.embeddings import EmbeddingsE5  # noqa: E402
from src.rag.errores import ErrorRAG  # noqa: E402
from src.rag.indexacion import indexar_archivo  # noqa: E402
from src.rag.recuperacion import recuperar  # noqa: E402
from src.rag.vectorstore import AlmacenChroma  # noqa: E402


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


def a_markdown(informe: dict[str, Any]) -> str:
    estado = (
        "ya estaba indexado (sin gasto)"
        if informe["reutilizado"]
        else f"indexado en {informe['segundos_indexar']} s"
    )
    lineas = [
        f"# T2-05 · Indexar y consultar ({informe['fecha']})",
        "",
        "**SIMULADO: puntajes de bolsa de palabras, no de e5.**" if informe["simulado"] else "",
        f"- Documento: `{informe['documento']}` · document_id `{informe['document_id']}`",
        f"- Chunks indexados: {informe['chunks']} · {estado}",
        f"- Consulta: «{informe['consulta']}» · umbral {informe['umbral']} · top {informe['top_k']}",
        f"- **Criterio de salida de T2-05: {'CUMPLE' if informe['cumple'] else 'NO CUMPLE'}** "
        f"({informe['sobre_umbral']} chunks sobre el umbral)",
        "",
        "| Chunk | Página | Puntaje | ¿Sobre el umbral? | Inicio del texto |",
        "|---|---|---|---|---|",
    ]
    for r in informe["resultados"]:
        lineas.append(
            f"| {r['chunk_id']} | {r['pagina'] or '-'} | {r['score']:.4f} | "
            f"{'sí' if r['sobre_umbral'] else 'no'} | {r['inicio']} |"
        )
    return "\n".join(linea for linea in lineas if linea is not None) + "\n"


def main(argumentos: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Criterio de salida de T2-05: indexar y consultar.")
    parser.add_argument("--documento", required=True, type=Path, help="PDF, Markdown o texto.")
    parser.add_argument("--consulta", default="Scrum Master")
    parser.add_argument("--forzar", action="store_true", help="Reindexa aunque ya esté indexado.")
    parser.add_argument("--salida", type=Path, help="Carpeta donde guardar el JSON y el Markdown.")
    parser.add_argument("--simular", action="store_true", help="Sin red ni token (índice temporal).")
    args = parser.parse_args(argumentos)

    if not args.documento.is_file():
        parser.error(f"no encuentro el documento: {args.documento}")

    try:
        config = cargar_config()
        if args.simular:
            config = dataclasses.replace(config, chroma_path=Path(tempfile.mkdtemp(prefix="chroma_simulado_")))
            embeddings: Embeddings = EmbeddingsSimulados(config.dimension_embeddings)
        else:
            embeddings = EmbeddingsE5(config)
        almacen = AlmacenChroma(config)
        print(f"Configuración: {config.resumen_seguro()}")
        print(f"Índice: {config.chroma_path}")

        inicio = time.perf_counter()
        document_id, cantidad = indexar_archivo(
            args.documento, embeddings=embeddings, almacen=almacen, forzar=args.forzar
        )
        segundos = round(time.perf_counter() - inicio, 2)
        gastados = embeddings.estadisticas.textos if isinstance(embeddings, EmbeddingsE5) else None
        reutilizado = gastados == 0

        todos = recuperar(document_id, args.consulta, umbral=-1.0, embeddings=embeddings, almacen=almacen)
    except ErrorRAG as err:
        print(f"Falló: {err}")
        return 1

    umbral = config.umbral_retrieval
    resultados = [
        {
            "chunk_id": r.chunk_id,
            "pagina": r.pagina,
            "score": round(r.score, 4),
            "sobre_umbral": r.score >= umbral,
            "inicio": " ".join(r.texto.split())[:100],
        }
        for r in todos
    ]
    sobre = sum(r["sobre_umbral"] for r in resultados)
    informe = {
        "fecha": datetime.now().astimezone().isoformat(timespec="seconds"),
        "simulado": args.simular,
        "documento": args.documento.name,
        "document_id": document_id,
        "chunks": cantidad,
        "reutilizado": reutilizado,
        "segundos_indexar": segundos,
        "textos_embebidos_al_indexar": gastados,
        "consulta": args.consulta,
        "umbral": umbral,
        "top_k": config.top_k,
        "sobre_umbral": sobre,
        "cumple": sobre > 0,
        "resultados": resultados,
    }
    resumen = a_markdown(informe)
    print()
    print(resumen)

    if args.salida:
        args.salida.mkdir(parents=True, exist_ok=True)
        base = f"T2-05_indexar_{datetime.now():%Y%m%d-%H%M%S}" + ("_simulado" if args.simular else "")
        (args.salida / f"{base}.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.salida / f"{base}.md").write_text(resumen, encoding="utf-8")
        print(f"Guardado: {base}.json y {base}.md en {args.salida}")

    return 0 if informe["cumple"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
