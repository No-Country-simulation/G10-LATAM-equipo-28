"""
NuevaMente — Dobles de prueba compartidos por las pruebas del RAG.

No es un archivo de pruebas (no empieza con test_): lo importan las pruebas
de chunking, índice, indexación y recuperación.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
from langchain_core.embeddings import Embeddings

DIMENSION = 768


class EmbeddingsFalsos(Embeddings):
    """
    Bolsa de palabras con hashing a 768 dimensiones, normalizada.

    Sin red y determinista: dos textos que comparten palabras se parecen, así
    que las pruebas de recuperación tienen sentido. Cuenta las llamadas para
    comprobar cuándo se gasta (o no) cuota.
    """

    def __init__(self, dimension: int = DIMENSION) -> None:
        self.dimension = dimension
        self.llamadas_documentos = 0
        self.textos_documentos = 0
        self.llamadas_consultas = 0

    def vector(self, texto: str) -> list[float]:
        v = np.zeros(self.dimension)
        for palabra in re.findall(r"\w+", texto.lower()):
            v[int(hashlib.md5(palabra.encode("utf-8")).hexdigest()[:8], 16) % self.dimension] += 1.0
        norma = np.linalg.norm(v)
        if norma == 0:
            v[0], norma = 1.0, 1.0
        return (v / norma).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.llamadas_documentos += 1
        self.textos_documentos += len(texts)
        return [self.vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        self.llamadas_consultas += 1
        return self.vector(text)

    def embeder_consultas(self, textos: list[str]) -> list[list[float]]:
        self.llamadas_consultas += 1
        return [self.vector(t) for t in textos]


def crear_pdf(ruta: Path, paginas: list[str]) -> Path:
    """PDF de prueba con reportlab (ya está en requirements.txt): una cadena por página."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    lienzo = canvas.Canvas(str(ruta), pagesize=A4)
    for texto in paginas:
        y = 800
        for linea in texto.split("\n"):
            lienzo.drawString(50, y, linea)
            y -= 14
        lienzo.showPage()
    lienzo.save()
    return ruta
