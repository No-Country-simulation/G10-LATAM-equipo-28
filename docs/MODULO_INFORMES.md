# Modulo de Informes y Exportacion Multiformato (NuevaMente)

**Responsable:** Victor Asencio
**Rama:** feature/victor-calidad

## 1. Descripcion
Modulo encargado de procesar la salida estructurada del pipeline (contrato PaqueteEducativo) y exportarla en PDF (ReportLab) y Markdown (.md).

## 2. Capacidades
- Generacion de PDF con encabezados, ficha tecnica, score de fidelidad RAG y citas de anclaje.
- Generacion de Markdown estructurado para plataformas como Notion/Obsidian.

## 3. Archivos
- src/generador_informes.py
- datos_demo/paquete_demo.json

## 4. Ejecucion
python src/generador_informes.py
python -m pytest tests -q
