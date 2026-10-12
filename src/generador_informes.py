import json
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generar_reporte_desde_json(datos_o_ruta_json, salida_pdf="informe_generado.pdf", salida_md="informe_generado.md"):
    if isinstance(datos_o_ruta_json, str):
        with open(datos_o_ruta_json, 'r', encoding='utf-8-sig') as f:
            datos = json.load(f)
    else:
        datos = datos_o_ruta_json

    materia = datos.get("materia", "Tema General")
    nivel = datos.get("nivel", "Intermedio")
    doc_origen = datos.get("documento_origen", "Documento base")
    score = datos.get("score_fidelidad", 0.95)
    resumen = datos.get("resumen", "Sin resumen disponible.")
    preguntas = datos.get("preguntas", [])
    citas = datos.get("citas_anclaje", [])

    # 1. MARKDOWN
    lineas_md = [
        f"# NuevaMente - Paquete Educativo: {materia}\n",
        f"**Nivel:** {nivel} | **Documento Origen:** {doc_origen} | **Score de Fidelidad:** {score:.2f}\n",
        "---\n",
        "## 1. Resumen Conceptual\n",
        f"{resumen}\n",
        "## 2. Preguntas de Autoevaluación y Respuestas Didácticas\n"
    ]
    for i, p in enumerate(preguntas, 1):
        lineas_md.append(f"### Pregunta {i}: {p.get('pregunta', '')}")
        lineas_md.append(f"**Respuesta:** {p.get('respuesta', '')}\n")
    
    if citas:
        lineas_md.append("## 3. Citas de Anclaje a la Fuente Técnica")
        for cita in citas:
            lineas_md.append(f"> *\"{cita}\"*\n")
            
    with open(salida_md, "w", encoding="utf-8") as f_md:
        f_md.write("\n".join(lineas_md))

    # 2. PDF CON REPORTLAB
    doc = SimpleDocTemplate(
        salida_pdf,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'TituloPrincipal',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=8
    )
    subtitulo_style = ParagraphStyle(
        'Subtitulo',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2563EB'),
        spaceAfter=6,
        spaceBefore=10
    )
    cuerpo_style = ParagraphStyle(
        'Cuerpo',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1F2937')
    )
    meta_style = ParagraphStyle(
        'Metadatos',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#374151')
    )

    story = []
    story.append(Paragraph(f"NuevaMente — {materia}", titulo_style))
    story.append(Paragraph(f"<b>Nivel Didáctico:</b> {nivel} | <b>Doc Origen:</b> {doc_origen}", subtitulo_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=12))

    tabla_meta = Table([
        [Paragraph(f"<b>Fidelidad RAG:</b> {score * 100:.1f}%", meta_style), 
         Paragraph("<b>Validación de Contrato:</b> PaqueteEducativo", meta_style)]
    ], colWidths=[260, 260])
    tabla_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
    ]))
    story.append(tabla_meta)
    story.append(Spacer(1, 12))

    story.append(Paragraph("1. Resumen Conceptual", subtitulo_style))
    story.append(Paragraph(resumen, cuerpo_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. Banco de Preguntas y Respuestas", subtitulo_style))
    for i, p in enumerate(preguntas, 1):
        story.append(Paragraph(f"<b>{i}. {p.get('pregunta', '')}</b>", cuerpo_style))
        story.append(Paragraph(f"<i>Respuesta:</i> {p.get('respuesta', '')}", cuerpo_style))
        story.append(Spacer(1, 6))

    if citas:
        story.append(Paragraph("3. Citas de Anclaje a la Fuente", subtitulo_style))
        for cita in citas:
            story.append(Paragraph(f"• <i>\"{cita}\"</i>", cuerpo_style))
            story.append(Spacer(1, 4))

    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#9CA3AF'), spaceAfter=8))
    story.append(Paragraph("Generado automáticamente por el módulo de Informes | NuevaMente", meta_style))

    doc.build(story)
    print(f"[OK] Reportes generados exitosamente:\n - PDF: {salida_pdf}\n - Markdown: {salida_md}")

if __name__ == "__main__":
    ruta_demo = os.path.join("datos_demo", "paquete_demo.json")
    if os.path.exists(ruta_demo):
        generar_reporte_desde_json(ruta_demo)
    else:
        print(f"[AVISO] No se encontró {ruta_demo}.")
