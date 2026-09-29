"""
NuevaMente — RAG: normalización, chunking, embeddings, índice y recuperación.

Cada módulo se importa por separado (`from src.rag.normalizador import ...`),
así cargar uno no arrastra las dependencias pesadas de los demás.

Dentro del paquete los imports son relativos y no dependen de nada fuera de
`src/rag/`. Por eso funciona de las dos formas en que se usa hoy:

  - como `src.rag`, desde la raíz del repo (pruebas y scripts);
  - como `rag`, con `src/` como directorio de trabajo (así corre `grafo.py`).
"""
