from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table as PDFTable, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime, timedelta
from src.config import console

from typing import List, Dict, Any, Union

def export_to_pdf(duties: List[Dict[str, Any]], filename: str = "dienstplan.pdf", title_text: str = "Dienstplan Übersicht") -> bool:
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
        except Exception:
            return False

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
        except (ValueError, AttributeError, KeyError, TypeError) as ex:
            pass  # Skip malformed duty entries

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

def export_absences_to_pdf(absences: List[Dict[str, Any]], filename: str = "abwesenheiten.pdf", title_text: str = "Meine Abwesenheiten") -> bool:
    """Generates a PDF for absences list."""
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
    
    # Headers
    data = [["Zeitraum", "Grund / Art", "Dauer"]]
    
    if not absences:
        elements.append(Paragraph("Keine Abwesenheiten gefunden.", styles['Normal']))
        try:
            doc.build(elements)
            return True
        except Exception:
            return False

    weekday_map = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

    for a in absences:
        try:
            b_raw = datetime.strptime(a['begin'], '%Y-%m-%dT%H:%M:%S')
            e_raw = datetime.strptime(a['end'], '%Y-%m-%dT%H:%M:%S')
            reason = a.get('duty_type', '')
            
            # Logic copy-paste from UI to keep consistency
            b = b_raw
            if b_raw.hour >= 20: 
                b = b_raw + timedelta(days=1)
                b = b.replace(hour=0, minute=0, second=0)

            e = e_raw
            if e_raw.hour == 0 and e_raw.minute == 0 and e_raw.second == 0:
                e = e_raw - timedelta(seconds=1)
            
            total_seconds = int((e_raw - b_raw).total_seconds())
            days_diff = (e.date() - b.date()).days + 1
            
            dur_str = ""
            if "urlaub" in reason.lower() or "abwesend" in reason.lower() or "sonderabwesenheit" in reason.lower() or "frei" in reason.lower() or total_seconds >= 86000:
                dur_str = "1 Tag" if days_diff == 1 else f"{days_diff} Tage"
            else:
                h = total_seconds / 3600
                dur_str = f"{int(h)} Std." if h == int(h) else f"{h:g} Std."

            wd_start = weekday_map[b.weekday()]
            date_str = f"{wd_start} {b.strftime('%d.%m.%Y')}"
            if e.date() > b.date():
                 wd_end = weekday_map[e.weekday()]
                 date_str = f"{wd_start} {b.strftime('%d.%m.')} - {wd_end} {e.strftime('%d.%m.%Y')}"

            data.append([
                date_str,
                reason,
                dur_str
            ])
        except (ValueError, KeyError, TypeError):
            pass  # Skip malformed absence entries

    # Column Widths (A4 Width ~ 450-500 printable)
    # Total ~ 450
    col_widths = [180, 180, 90]
    
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
        
        # Striping
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
        return True
    except Exception as e:
        console.print(f"[error]Fehler beim Erstellen des PDF: {e}[/error]")
        return False
