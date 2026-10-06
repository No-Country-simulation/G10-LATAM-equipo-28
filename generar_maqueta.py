import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generar_maqueta_pdf(ruta_salida="informe_maqueta.pdf"):
    doc = SimpleDocTemplate(
        ruta_salida,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    titulo_style = ParagraphStyle(
        'TituloPrincipal',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=10
    )
    subtitulo_style = ParagraphStyle(
        'Subtitulo',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#2563EB'),
        spaceAfter=8
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
        textColor=colors.HexColor('#4B5563')
    )

    story = []

    # Encabezado
    story.append(Paragraph("NuevaMente - Paquete Educativo Generado", titulo_style))
    story.append(Paragraph("<b>Materia:</b> Fundamentos de Infraestructura y Datos | <b>Nivel:</b> Intermedio", subtitulo_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=15))

    # Ficha Técnica / Metadatos de Validación
    story.append(Paragraph("<b>Ficha Técnica de Control de Calidad:</b>", cuerpo_style))
    datos_meta = [
        [Paragraph("<b>Score de Fidelidad:</b> 0.94 / 1.00", meta_style), Paragraph("<b>Anclaje a Fuentes:</b> 100% verificado", meta_style)],
        [Paragraph("<b>Documento Origen:</b> doc3_oci_storage.pdf", meta_style), Paragraph("<b>Motor RAG:</b> LangGraph + Gemini", meta_style)]
    ]
    tabla_meta = Table(datos_meta, colWidths=[260, 260])
    tabla_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(tabla_meta)
    story.append(Spacer(1, 15))

    # Sección 1: Resumen Ejecutivo
    story.append(Paragraph("1. Resumen Conceptual", subtitulo_style))
    story.append(Paragraph(
        "El presente informe sintetiza los principios arquitectonicos de almacenamiento en la nube orientados a "
        "la persistencia y alta disponibilidad. La solucion aborda la redundancia distribuida y el cifrado en reposo "
        "garantizando la integridad de los activos de informacion del sistema.",
        cuerpo_style
    ))
    story.append(Spacer(1, 12))

    # Sección 2: Desarrollo Didáctico
    story.append(Paragraph("2. Desarrollo y Preguntas Clave", subtitulo_style))
    story.append(Paragraph(
        "<b>Pregunta 1:</b> Que caracteristica garantiza que un objeto almacenado no sufra corrupcion silenciosa?<br/>"
        "<i>Respuesta didactica:</i> La combinacion de sumas de verificacion automaticas (checksums) y el ciclo de vida continuo del almacenamiento en buckets redundantes.",
        cuerpo_style
    ))
    story.append(Spacer(1, 12))

    # Sección 3: Evidencia de anclaje (Citas directas)
    story.append(Paragraph("3. Citas de Anclaje a la Fuente Tecnica", subtitulo_style))
    story.append(Paragraph(
        "<i>\"Object Storage es un servicio de almacenamiento escalable y de alta durabilidad con redundancia en multiples dominios de disponibilidad.\"</i> (Chunk ref: #003)",
        cuerpo_style
    ))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#9CA3AF'), spaceAfter=10))
    story.append(Paragraph("Generado por NuevaMente | Hackathon ONE G10 - Equipo 28", meta_style))

    doc.build(story)
    print("Maqueta PDF generada con exito: " + ruta_salida)

if __name__ == '__main__':
    generar_maqueta_pdf()
