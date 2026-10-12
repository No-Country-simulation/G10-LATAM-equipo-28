# Módulo de Informes y Exportación Multiformato (NuevaMente)

**Responsable del carril:** Víctor Asencio  
**Rama:** `feature/victor-calidad`  

## 1. Descripción
El módulo de Informes es el componente encargado de procesar la salida estructurada generada por el pipeline de agentes (conforme al contrato `PaqueteEducativo`) y exportarla en múltiples formatos de alta fidelidad pedagógica y técnica.

## 2. Capacidades y Formatos
- **Exportación en PDF profesional (ReportLab):**
  - Encabezados institucionales y tipografía adaptada.
  - Ficha técnica de control de calidad con métricas de fidelidad RAG.
  - Desglose didáctico de preguntas, respuestas explicadas y conceptos clave.
  - Citas de anclaje contextual a las fuentes técnicas procesadas.
- **Exportación en Markdown estructurado (.md):**
  - Formato estandarizado compatible con plataformas de gestión del conocimiento (Notion, Obsidian, GitHub).
  - Jerarquía clara de títulos, listas y bloques de citas (`>`).

## 3. Arquitectura y Archivos Clave
- `src/generador_informes.py`: Motor de transformación de datos JSON/diccionarios a PDF y Markdown.
- `datos_demo/paquete_demo.json`: Dataset de validación local del contrato `PaqueteEducativo`.

## 4. Guía de Ejecución Local
Para validar la generación autónoma de los informes:
```bash
# Ejecución del generador dinámico
python src/generador_informes.py

# Verificación de la suite de pruebas unitarias
python -m pytest tests -q
