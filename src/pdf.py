from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table as PDFTable, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
from src.config import console

def export_to_pdf(duties, filename="dienstplan.pdf", title_text="Dienstplan Übersicht"):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Colors
    rk_red = colors.HexColor("#E3001B")
    light_grey = colors.HexColor("#F2F2F2")
    
    # Title Block
    title = Paragraph(title_text, styles['Title'])
    elements.append(title)
    
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    elements.append(Paragraph(f"Erstellt am: {timestamp}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    data = [["Datum", "Zeit", "Std.", "Fahrzeug", "Besatzung"]]
    
    if not duties:
        elements.append(Paragraph("Keine Dienste gefunden.", styles['Normal']))
        try:
            doc.build(elements)
            return True
        except: return False

    for d in duties:
        try:
            # Parse Dates
            b, e = d.get('begin'), d.get('end')
            
            # If string, parse it
            if isinstance(b, str):
                if 'T' in b: b = datetime.strptime(b[:19], '%Y-%m-%dT%H:%M:%S')
                else: b = datetime.strptime(b, '%Y-%m-%d %H:%M:%S')
            
            if isinstance(e, str):
                if 'T' in e: e = datetime.strptime(e[:19], '%Y-%m-%dT%H:%M:%S')
                else: e = datetime.strptime(e, '%Y-%m-%d %H:%M:%S')
            
            # If still not datetime (e.g. None), skip or handle
            if not isinstance(b, datetime) or not isinstance(e, datetime):
                continue
                
            h = (e - b).total_seconds() / 3600
            
            # Format Crew
            crew_raw = d.get('crew')
            crew_str = "-"
            
            if isinstance(crew_raw, list):
                crew_str = "\n".join(crew_raw)
            elif isinstance(crew_raw, dict):
                # Format dict (e.g. daily plan)
                parts = []
                if "FAHRER" in crew_raw: parts.append(f"F: {crew_raw['FAHRER']}")
                if "SANITAETER1" in crew_raw: parts.append(f"S1: {crew_raw['SANITAETER1']}")
                if "SANITAETER2" in crew_raw: parts.append(f"S2: {crew_raw['SANITAETER2']}")
                # Add others if any
                for k, v in crew_raw.items():
                    if k not in ["FAHRER", "SANITAETER1", "SANITAETER2"]:
                        parts.append(f"{k}: {v}")
                crew_str = "\n".join(parts)
            elif isinstance(crew_raw, str):
                crew_str = crew_raw
                
            if not crew_str: crew_str = "-"

            data.append([
                b.strftime('%d.%m.%Y'),
                f"{b.strftime('%H:%M')} - {e.strftime('%H:%M')}",
                f"{h:.1f}h",
                d.get('vehicle') or "-",
                crew_str
            ])
        except Exception as ex: 
            # console.print(f"Debug PDF Error: {ex}") 
            pass

    # Column Widths
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
        # console.print(f"[success]PDF gespeichert als: {filename}[/success]")
        return True
    except Exception as e:
        console.print(f"[error]Fehler beim Erstellen des PDF: {e}[/error]")
        return False
