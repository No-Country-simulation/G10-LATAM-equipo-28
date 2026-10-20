"""
NuevaMente — Prueba en vivo de los embeddings e5 por la API de Hugging Face (T2-06).

No es parte de pytest: llama a la API real y gasta cuota (unos 70 textos en
7 peticiones, más los reintentos si los hay).

Uso, desde la raíz del repo y con el .venv activo:

    python scripts/probar_embeddings_api.py --pdf "RUTA/guía.pdf" --salida "CARPETA" --etiqueta gitbash

    --simular    Corre todo con un cliente falso, sin red ni token. Sirve para
                 revisar que el script funciona antes de gastar cuota; sus
                 puntajes no significan nada.

Qué mide:
  A. Responde: dimensión y latencia de una petición.
  B. Lotes de 8, 16 y 32 textos: latencia por lote y por texto.
  C. Prefijos y umbral: consultas del tema y ajenas contra los chunks, para ver
     si UMBRAL_RETRIEVAL separa lo relevante de lo ajeno, y una consulta sin
     prefijo para comparar. Las consultas están pensadas para la guía del
     Scrum Master.
  D. Texto largo (~3.000 caracteres): si la API lo acepta, lo trunca o lo
     rechaza.
  E. Normas de los vectores tal como llegan de la API.

El token se lee del .env (HF_TOKEN) y nunca se imprime ni se guarda.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.rag import errores as e  # noqa: E402
from src.rag.configuracion import ConfigRAG, cargar_config  # noqa: E402
from src.rag.embeddings import EmbeddingsE5  # noqa: E402
from src.rag.errores import ErrorRAG  # noqa: E402
from src.rag.normalizador import normalizar_paginas  # noqa: E402

CONSULTAS_DEL_TEMA = [
    "¿Qué hace el Scrum Master?",
    "Scrum Master",
    "responsabilidades del Scrum Master con el Product Owner",
]
CONSULTAS_AJENAS = [
    "receta de arepas antioqueñas",
    "normativa RETIE para subestaciones eléctricas",
]
CONSULTA_SIN_PREFIJO = "Scrum Master"
LOTES_POR_DEFECTO = "8,16,32"
LARGO_TEXTO_LARGO = 3000
MINIMO_CARACTERES_CHUNK = 200

#: Errores que hacen inútil seguir probando: se corta y se informa.
_ERRORES_QUE_DETIENEN = {
    e.EMBEDDINGS_SIN_TOKEN,
    e.EMBEDDINGS_TOKEN_INVALIDO,
    e.EMBEDDINGS_SIN_CREDITOS,
    e.EMBEDDINGS_MODELO_NO_ENCONTRADO,
    e.EMBEDDINGS_NO_DISPONIBLE,
}


# =============================================================================
# Apoyo
# =============================================================================


class ClienteSimulado:
    """Vectores deterministas sin red: solo para revisar el flujo del script."""

    def __init__(self, dimension: int) -> None:
        self.dimension = dimension

    def feature_extraction(self, text: str | list[str], **kwargs: Any) -> np.ndarray:
        textos = [text] if isinstance(text, str) else list(text)
        filas = []
        for texto in textos:
            semilla = int(hashlib.sha256(texto.encode("utf-8")).hexdigest()[:8], 16)
            filas.append(np.random.default_rng(semilla).normal(size=self.dimension))
        time.sleep(0.01)
        return np.array(filas)


class Banco:
    """Crea las instancias de EmbeddingsE5 y suma sus estadísticas."""

    def __init__(self, config: ConfigRAG, simular: bool) -> None:
        self.config = config
        self.simular = simular
        self.instancias: list[EmbeddingsE5] = []

    def nuevo(self, parametros_api: dict[str, Any] | None = None, **cambios: Any) -> EmbeddingsE5:
        config = dataclasses.replace(self.config, **cambios) if cambios else self.config
        cliente = ClienteSimulado(config.dimension_embeddings) if self.simular else None
        emb = EmbeddingsE5(config, cliente=cliente, parametros_api=parametros_api)
        self.instancias.append(emb)
        return emb

    def totales(self) -> dict[str, Any]:
        claves = ("peticiones", "peticiones_fallidas", "reintentos", "textos", "caracteres")
        total: dict[str, Any] = {c: sum(getattr(i.estadisticas, c) for i in self.instancias) for c in claves}
        total["segundos"] = round(sum(i.estadisticas.segundos for i in self.instancias), 3)
        estadisticas = [i.estadisticas for i in self.instancias]
        minimos = [s.norma_cruda_min for s in estadisticas if s.norma_cruda_min is not None]
        maximos = [s.norma_cruda_max for s in estadisticas if s.norma_cruda_max is not None]
        total["norma_cruda_min"] = round(min(minimos), 4) if minimos else None
        total["norma_cruda_max"] = round(max(maximos), 4) if maximos else None
        return total


def error_como_dict(err: ErrorRAG) -> dict[str, Any]:
    return {"ok": False, "codigo": err.codigo, "mensaje": err.mensaje, "detalle": err.detalle}


def cronometrar(funcion, *argumentos):
    inicio = time.perf_counter()
    resultado = funcion(*argumentos)
    return resultado, round(time.perf_counter() - inicio, 3)


def extraer_chunks(pdf: Path, config: ConfigRAG) -> tuple[list[str], dict[str, Any]]:
    """PDF -> páginas -> normalizador -> chunks de CHUNK_SIZE/CHUNK_OVERLAP."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from pypdf import PdfReader

    paginas = [(pagina.extract_text() or "") for pagina in PdfReader(str(pdf)).pages]
    texto = normalizar_paginas(paginas)
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap
    )
    todos = divisor.split_text(texto)
    utiles = [c for c in todos if len(c.strip()) >= MINIMO_CARACTERES_CHUNK]
    info = {
        "archivo": pdf.name,
        "paginas": len(paginas),
        "caracteres_normalizados": len(texto),
        "chunks_totales": len(todos),
        "chunks_de_200_o_mas": len(utiles),
    }
    return utiles, info


def elegir_repartidos(chunks: list[str], cantidad: int) -> list[str]:
    """Toma `cantidad` chunks repartidos a lo largo del documento."""
    if len(chunks) <= cantidad:
        return list(chunks)
    indices = sorted({int(i) for i in np.linspace(0, len(chunks) - 1, cantidad).round()})
    return [chunks[i] for i in indices]


# =============================================================================
# Pruebas
# =============================================================================


def prueba_a(banco: Banco, chunk: str) -> dict[str, Any]:
    emb = banco.nuevo(tamano_lote=1)
    try:
        vectores, segundos = cronometrar(emb.embed_documents, [chunk])
    except ErrorRAG as err:
        return error_como_dict(err)
    return {"ok": True, "dimension": len(vectores[0]), "segundos": segundos}


Muestra = tuple[list[str], list[list[float]]]


def prueba_b(banco: Banco, textos: list[str], lotes: list[int]) -> tuple[list[dict[str, Any]], Muestra | None]:
    resultados: list[dict[str, Any]] = []
    mejor: Muestra | None = None
    for tamano in lotes:
        # Si el documento da menos chunks que el lote, se repiten para llenarlo:
        # sirve igual para medir latencia y límites de la API.
        muestra = [textos[i % len(textos)] for i in range(tamano)]
        distintos = min(tamano, len(textos))
        emb = banco.nuevo(tamano_lote=tamano)
        try:
            vectores, segundos = cronometrar(emb.embed_documents, muestra)
        except ErrorRAG as err:
            resultados.append({"tamano": tamano, **error_como_dict(err)})
            if err.codigo in _ERRORES_QUE_DETIENEN:
                break
            continue
        resultados.append({
            "tamano": tamano,
            "ok": True,
            "segundos": segundos,
            "segundos_por_texto": round(segundos / tamano, 4),
            "reintentos": emb.estadisticas.reintentos,
            "chunks_repetidos": tamano - distintos,
        })
        # Para la prueba C solo sirven los chunks distintos.
        mejor = (muestra[:distintos], vectores[:distintos])
    return resultados, mejor


def prueba_c(banco: Banco, textos: list[str], vectores: list[list[float]]) -> dict[str, Any]:
    umbral = banco.config.umbral_retrieval
    emb = banco.nuevo()
    try:
        con_prefijo = emb.embeder_consultas(CONSULTAS_DEL_TEMA + CONSULTAS_AJENAS)
        sin_prefijo = emb.embeber([CONSULTA_SIN_PREFIJO], prefijo="")
    except ErrorRAG as err:
        return error_como_dict(err)

    matriz = np.array(vectores)
    casos = (
        [(c, "tema") for c in CONSULTAS_DEL_TEMA]
        + [(c, "ajena") for c in CONSULTAS_AJENAS]
        + [(f"{CONSULTA_SIN_PREFIJO} (sin prefijo)", "sin_prefijo")]
    )
    consultas = []
    for (consulta, tipo), vector in zip(casos, con_prefijo + sin_prefijo, strict=True):
        puntajes = matriz @ np.array(vector)
        orden = np.argsort(-puntajes)[:5]
        consultas.append({
            "consulta": consulta,
            "tipo": tipo,
            "max": round(float(puntajes.max()), 4),
            "media": round(float(puntajes.mean()), 4),
            "min": round(float(puntajes.min()), 4),
            "chunks_sobre_umbral": int((puntajes >= umbral).sum()),
            "top5": [
                {"puntaje": round(float(puntajes[i]), 4), "chunk": int(i), "inicio": " ".join(textos[i].split())[:90]}
                for i in orden
            ],
        })

    tema = [c for c in consultas if c["tipo"] == "tema"]
    ajenas = [c for c in consultas if c["tipo"] == "ajena"]
    min_top1_tema = min(c["max"] for c in tema)
    max_top1_ajena = max(c["max"] for c in ajenas)
    return {
        "ok": True,
        "umbral": umbral,
        "chunks_comparados": len(matriz),
        "min_top1_tema": min_top1_tema,
        "max_top1_ajena": max_top1_ajena,
        "margen": round(min_top1_tema - max_top1_ajena, 4),
        "chunks_ajenos_sobre_umbral": sum(c["chunks_sobre_umbral"] for c in ajenas),
        "umbral_separa": min_top1_tema >= umbral > max_top1_ajena,
        "consultas": consultas,
    }


def prueba_d(banco: Banco, chunks: list[str]) -> dict[str, Any]:
    largo = " ".join(" ".join(chunks).split())[:LARGO_TEXTO_LARGO]
    resultado: dict[str, Any] = {"caracteres": len(largo), "intentos": []}
    for nombre, parametros in (("sin_parametros", {}), ("truncate", {"truncate": True})):
        emb = banco.nuevo(parametros_api=parametros, tamano_lote=1, reintentos=1)
        try:
            _, segundos = cronometrar(emb.embed_documents, [largo])
        except ErrorRAG as err:
            resultado["intentos"].append({"variante": nombre, **error_como_dict(err)})
            if err.codigo != e.EMBEDDINGS_ENTRADA_INVALIDA:
                break  # otro tipo de falla: probar con truncate no aclara nada
            continue
        resultado["intentos"].append({"variante": nombre, "ok": True, "segundos": segundos})
        break
    resultado["ok"] = any(i.get("ok") for i in resultado["intentos"])
    return resultado


# =============================================================================
# Informe
# =============================================================================


def veredicto(informe: dict[str, Any]) -> dict[str, Any]:
    a_ok = informe["A"].get("ok", False)
    lotes_ok = [b["tamano"] for b in informe.get("B", []) if b.get("ok")]
    c_ok = informe.get("C", {}).get("ok", False)
    cumple = a_ok and any(t >= 8 for t in lotes_ok) and c_ok
    return {
        "cumple_criterio_T2_06": bool(cumple),
        "responde": a_ok,
        "lotes_ok": lotes_ok,
        "lote_recomendado": max(lotes_ok) if lotes_ok else None,
        "prefijos_probados": c_ok,
    }


def a_markdown(informe: dict[str, Any]) -> str:
    cfg, doc, ver, tot = informe["config"], informe["documento"], informe["veredicto"], informe["totales"]
    lineas = [
        f"# T2-06 · Prueba de embeddings e5 por API ({informe['etiqueta']})",
        "",
        f"- Fecha: {informe['fecha']}"
        + ("  ·  **SIMULADO: los puntajes no significan nada**" if informe["simulado"] else ""),
        f"- Modelo: `{cfg['modelo']}` · proveedor `{cfg['proveedor']}` · timeout {cfg['timeout_segundos']} s",
        f"- Documento: `{doc.get('archivo')}` · {doc.get('paginas')} páginas · "
        f"{doc.get('chunks_totales')} chunks de {cfg['chunk_size']}/{cfg['chunk_overlap']}",
        f"- **Criterio de salida de T2-06: {'CUMPLE' if ver['cumple_criterio_T2_06'] else 'NO CUMPLE'}**",
        "",
        "## A. Responde",
        "",
    ]
    a = informe["A"]
    lineas.append(
        f"Dimensión {a['dimension']} en {a['segundos']} s." if a.get("ok")
        else f"Falló: `{a.get('codigo')}`. {a.get('mensaje')} {a.get('detalle', '')}"
    )

    lineas += [
        "",
        "## B. Lotes",
        "",
        "| Lote | Resultado | Segundos | s/texto | Reintentos | Chunks repetidos |",
        "|---|---|---|---|---|---|",
    ]
    for b in informe.get("B", []):
        if b.get("ok"):
            lineas.append(
                f"| {b['tamano']} | OK | {b['segundos']} | {b['segundos_por_texto']} | "
                f"{b['reintentos']} | {b['chunks_repetidos']} |"
            )
        else:
            lineas.append(f"| {b['tamano']} | {b.get('codigo')} | | | | |")

    c = informe.get("C", {})
    lineas += ["", "## C. Prefijos y umbral", ""]
    if c.get("ok"):
        lineas += [
            f"Umbral {c['umbral']} contra {c['chunks_comparados']} chunks. "
            f"Top-1 más bajo de las consultas del tema: **{c['min_top1_tema']}**. "
            f"Top-1 más alto de las ajenas: **{c['max_top1_ajena']}** (margen {c['margen']}). "
            f"Chunks ajenos sobre el umbral: **{c['chunks_ajenos_sobre_umbral']}**. "
            f"¿El umbral separa? **{'sí' if c['umbral_separa'] else 'no'}**.",
            "",
            "| Consulta | Tipo | Máx | Media | Mín | Sobre umbral |",
            "|---|---|---|---|---|---|",
        ]
        for q in c["consultas"]:
            lineas.append(
                f"| {q['consulta']} | {q['tipo']} | {q['max']} | {q['media']} | {q['min']} | "
                f"{q['chunks_sobre_umbral']} |"
            )
    elif c:
        lineas.append(f"Falló: `{c.get('codigo')}`. {c.get('detalle', '')}")
    else:
        lineas.append("No se corrió.")

    d = informe.get("D")
    lineas += ["", "## D. Texto largo", ""]
    if d:
        for intento in d["intentos"]:
            estado = "OK" if intento.get("ok") else intento.get("codigo")
            lineas.append(f"- {d['caracteres']} caracteres, variante `{intento['variante']}`: {estado}")
    else:
        lineas.append("No se corrió.")

    lineas += [
        "",
        "## E. Normas y consumo",
        "",
        f"- Norma de los vectores tal como llegan: {tot['norma_cruda_min']} a {tot['norma_cruda_max']} "
        "(1,0 = ya vienen normalizados; el RAG los normaliza igual).",
        f"- Peticiones: {tot['peticiones']} ({tot['peticiones_fallidas']} fallidas, {tot['reintentos']} reintentos) · "
        f"textos: {tot['textos']} · caracteres: {tot['caracteres']} · tiempo en la API: {tot['segundos']} s.",
        "- Costo: compara el consumo de huggingface.co/settings/billing antes y después de correr esto.",
        "",
    ]
    return "\n".join(lineas)


# =============================================================================
# Programa
# =============================================================================


def main(argumentos: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.WARNING, format="  aviso: %(message)s")

    parser = argparse.ArgumentParser(description="Prueba en vivo de los embeddings e5 por API (T2-06).")
    parser.add_argument("--pdf", required=True, type=Path, help="PDF de prueba (una guía de 04_insumos).")
    parser.add_argument("--salida", type=Path, help="Carpeta donde guardar el JSON y el Markdown.")
    parser.add_argument("--etiqueta", default="local", help="Nombre de la corrida: gitbash, sandbox...")
    parser.add_argument("--lotes", default=LOTES_POR_DEFECTO, help="Tamaños de lote a probar, separados por coma.")
    parser.add_argument("--sin-texto-largo", action="store_true", help="Omite la prueba D.")
    parser.add_argument("--simular", action="store_true", help="Sin red ni token, con un cliente falso.")
    args = parser.parse_args(argumentos)

    if not args.pdf.is_file():
        parser.error(f"no encuentro el PDF: {args.pdf}")
    try:
        lotes = sorted({int(x) for x in args.lotes.split(",") if x.strip()})
    except ValueError:
        parser.error("--lotes debe ser una lista de enteros, por ejemplo 8,16,32")

    try:
        config = cargar_config()
    except ErrorRAG as err:
        print(f"Configuración inválida: {err}")
        return 1
    print(f"Configuración: {config.resumen_seguro()}")
    if args.simular:
        print("MODO SIMULADO: sin red ni token; los puntajes no significan nada.")

    chunks, info_documento = extraer_chunks(args.pdf, config)
    if not chunks:
        print("El PDF no dio chunks útiles: revisa que tenga texto extraíble.")
        return 1
    seleccion = elegir_repartidos(chunks, max(lotes))
    print(f"Documento: {info_documento['archivo']} · {info_documento['paginas']} páginas · "
          f"{info_documento['chunks_totales']} chunks · muestra de {len(seleccion)}")

    banco = Banco(config, args.simular)
    informe: dict[str, Any] = {
        "fecha": datetime.now().astimezone().isoformat(timespec="seconds"),
        "etiqueta": args.etiqueta,
        "simulado": args.simular,
        "config": {
            "modelo": config.modelo_embeddings,
            "proveedor": config.proveedor_embeddings,
            "dimension": config.dimension_embeddings,
            "timeout_segundos": config.timeout_segundos,
            "reintentos": config.reintentos,
            "chunk_size": config.chunk_size,
            "chunk_overlap": config.chunk_overlap,
            "umbral_retrieval": config.umbral_retrieval,
            "token_presente": config.tiene_token,
        },
        "documento": info_documento,
    }

    print("A. ¿Responde?...")
    informe["A"] = prueba_a(banco, seleccion[0])
    if informe["A"].get("ok"):
        print("B. Lotes...")
        informe["B"], mejor = prueba_b(banco, seleccion, lotes)
        if mejor is not None:
            print("C. Prefijos y umbral...")
            informe["C"] = prueba_c(banco, *mejor)
        if not args.sin_texto_largo:
            print("D. Texto largo...")
            informe["D"] = prueba_d(banco, chunks)
    elif informe["A"].get("codigo") in _ERRORES_QUE_DETIENEN:
        print(f"Se detiene: {informe['A'].get('codigo')}.")

    informe["totales"] = banco.totales()
    informe["veredicto"] = veredicto(informe)
    resumen = a_markdown(informe)
    print()
    print(resumen)

    if args.salida:
        args.salida.mkdir(parents=True, exist_ok=True)
        base = f"T2-06_embeddings_{args.etiqueta}_{datetime.now():%Y%m%d-%H%M%S}"
        ruta_json = args.salida / f"{base}.json"
        ruta_md = args.salida / f"{base}.md"
        ruta_json.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
        ruta_md.write_text(resumen, encoding="utf-8")
        print(f"Guardado: {ruta_json.name} y {ruta_md.name} en {args.salida}")

    return 0 if informe["veredicto"]["cumple_criterio_T2_06"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
