from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table as PDFTable, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
from src.config import console

def export_to_pdf(duties, filename="dienstplan.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Colors
    rk_red = colors.HexColor("#E3001B")
    light_grey = colors.HexColor("#F2F2F2")
    
    # Title Block
    title = Paragraph("Dienstplan Übersicht", styles['Title'])
    elements.append(title)
    
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    elements.append(Paragraph(f"Erstellt am: {timestamp}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    data = [["Datum", "Zeit", "Std.", "Fahrzeug", "Besatzung"]]
    
    for d in duties:
        try:
            # Parse Dates
            if 'T' in d['begin']:
                # Format: 2023-01-01T12:00:00
                b = datetime.strptime(d['begin'], '%Y-%m-%dT%H:%M:%S')
                e = datetime.strptime(d['end'], '%Y-%m-%dT%H:%M:%S')
            else:
                # Fallback if format differs
                b = datetime.strptime(d['begin'], '%Y-%m-%d %H:%M:%S')
                e = datetime.strptime(d['end'], '%Y-%m-%d %H:%M:%S')
                
            h = (e - b).total_seconds() / 3600
            
            # Format Crew: Replace newlines or commas with breaks if needed, 
            # but for the table list, we use a simple string. 
            # ReportLab supports Paragraphs in cells for wrapping, but simple string is often safer for layout.
            crew_list = d['crew']
            if isinstance(crew_list, list):
                crew_str = "\n".join(crew_list)
            else:
                crew_str = str(crew_list)
                
            if not crew_str: crew_str = "-"

            data.append([
                b.strftime('%d.%m.%Y'),
                f"{b.strftime('%H:%M')} - {e.strftime('%H:%M')}",
                f"{h:g}h",
                d['vehicle'] or "-",
                crew_str
            ])
        except Exception as ex: 
            # In case of parsing error, add raw or skip
            # console.print(f"Debug PDF Error: {ex}") 
            pass

    # Column Widths (A4 Width approx 595 points minus margins)
    # Total available approx 450-500 depending on margins.
    col_widths = [70, 90, 40, 90, 160]
    
    table = PDFTable(data, colWidths=col_widths, repeatRows=1)
    
    table_style = TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), rk_red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        
        # Striping (Zebra)
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_grey]),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ])
    
    table.setStyle(table_style)
    
    elements.append(table)
    try:
        doc.build(elements)
        console.print(f"[success]PDF gespeichert als: {filename}[/success]")
        return True
    except Exception as e:
        console.print(f"[error]Fehler beim Erstellen des PDF: {e}[/error]")
        return False
