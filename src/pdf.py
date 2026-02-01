"""
PDF export functionality for incode-cli.

This module provides functions to generate professional PDF reports
for duty schedules and absences using ReportLab.
"""
import logging
from reportlab.lib import colors

logger = logging.getLogger(__name__)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table as PDFTable, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime, timedelta
from dataclasses import asdict, is_dataclass
from src.config import console
from src.utils import parse_iso_datetime

from typing import List, Dict, Any, Union, Sequence
from src.models import Duty


def export_to_pdf(duties: Sequence[Union[Dict[str, Any], Duty]], filename: str = "dienstplan.pdf", title_text: str = "Dienstplan Übersicht") -> bool:
    """
    Export duties to a formatted PDF document.
    
    Creates a professional-looking PDF with Red Cross themed styling,
    including a table of all duties with date, time, duration, vehicle,
    and crew information.
    
    Args:
        duties: List of duties (as Dicts or Duty objects).
        filename: Output filename (default: 'dienstplan.pdf').
        title_text: Title to display at the top of the PDF.
        
    Returns:
        True if export was successful, False otherwise.
    """
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Colors - Red Cross theme
    rk_red = colors.HexColor("#E3001B")
    light_grey = colors.HexColor("#F2F2F2")
    
    # Title Block
    title = Paragraph(title_text, styles['Title'])
    elements.append(title)
    
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    elements.append(Paragraph(f"Erstellt am: {timestamp}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Table header
    data = [["Datum", "Zeit", "Std.", "Fahrzeug", "Besatzung"]]
    
    if not duties:
        elements.append(Paragraph("Keine Dienste gefunden.", styles['Normal']))
        try:
            doc.build(elements)
            return True
        except Exception as exc:
            logger.error(f"PDF export failed (no duties): {exc}")
            console.print(f"[error]Fehler beim Erstellen des PDF: {exc}[/error]")
            return False

    for item in duties:
        try:
            # Support both Dicts and Dataclasses
            d: Dict[str, Any] = asdict(item) if is_dataclass(item) else item            # Parse Dates - handle both string and datetime inputs
            b = parse_iso_datetime(d.get('begin'))
            e = parse_iso_datetime(d.get('end'))

            if not b or not e:
                continue
                
            h = (e - b).total_seconds() / 3600
            
            # Format Crew - handle list, dict, or string
            crew_raw = d.get('crew')
            crew_str = "-"
            
            if isinstance(crew_raw, list):
                crew_str = "\n".join(crew_raw)
            elif isinstance(crew_raw, dict):
                # Format dict (e.g. from daily plan)
                parts = []
                if "FAHRER" in crew_raw: 
                    parts.append(f"F: {crew_raw['FAHRER']}")
                if "SANITAETER1" in crew_raw: 
                    parts.append(f"S1: {crew_raw['SANITAETER1']}")
                if "SANITAETER2" in crew_raw: 
                    parts.append(f"S2: {crew_raw['SANITAETER2']}")
                # Add any other roles
                for k, v in crew_raw.items():
                    if k not in ["FAHRER", "SANITAETER1", "SANITAETER2"]:
                        parts.append(f"{k}: {v}")
                crew_str = "\n".join(parts)
            elif isinstance(crew_raw, str):
                crew_str = crew_raw
                
            if not crew_str: 
                crew_str = "-"

            data.append([
                b.strftime('%d.%m.%Y'),
                f"{b.strftime('%H:%M')} - {e.strftime('%H:%M')}",
                f"{h:.1f}h",
                d.get('vehicle') or "-",
                crew_str
            ])
        except (ValueError, AttributeError, KeyError, TypeError) as e:
            logger.debug(f"Skipping malformed duty entry: {e}")

    # Column Widths optimized for A4
    col_widths = [70, 90, 40, 90, 160]
    
    table = PDFTable(data, colWidths=col_widths, repeatRows=1)
    
    table_style = TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), rk_red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Row styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        
        # Zebra striping for readability
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
    except Exception as exc:
        logger.error(f"PDF export failed (duties): {exc}")
        console.print(f"[error]Fehler beim Erstellen des PDF: {exc}[/error]")
        return False


def export_absences_to_pdf(absences: List[Dict[str, Any]], filename: str = "abwesenheiten.pdf", title_text: str = "Meine Abwesenheiten") -> bool:
    """
    Generate a PDF report of absences (vacation, sick leave, etc.).
    
    Creates a formatted PDF document listing all absences with their
    time periods, reasons, and durations.
    
    Args:
        absences: List of absence dictionaries with 'begin', 'end', and 'duty_type' keys.
        filename: Output filename (default: 'abwesenheiten.pdf').
        title_text: Title to display at the top of the PDF.
        
    Returns:
        True if export was successful, False otherwise.
    """
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
        except Exception as exc:
            logger.error(f"PDF export failed (no absences): {exc}")
            console.print(f"[error]Fehler beim Erstellen des PDF: {exc}[/error]")
            return False

    weekday_map = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

    for a in absences:
        try:
            b_raw = parse_iso_datetime(a.get('begin'))
            e_raw = parse_iso_datetime(a.get('end'))
            if not b_raw or not e_raw:
                continue
            reason = a.get('duty_type', '')
            
            # Adjust times for display (handle overnight shifts)
            b = b_raw
            if b_raw.hour >= 20: 
                b = b_raw + timedelta(days=1)
                b = b.replace(hour=0, minute=0, second=0)

            e = e_raw
            if e_raw.hour == 0 and e_raw.minute == 0 and e_raw.second == 0:
                e = e_raw - timedelta(seconds=1)
            
            total_seconds = int((e_raw - b_raw).total_seconds())
            days_diff = (e.date() - b.date()).days + 1
            
            # Format duration based on absence type
            dur_str = ""
            if "urlaub" in reason.lower() or "abwesend" in reason.lower() or "sonderabwesenheit" in reason.lower() or "frei" in reason.lower() or total_seconds >= 86000:
                dur_str = "1 Tag" if days_diff == 1 else f"{days_diff} Tage"
            else:
                h = total_seconds / 3600
                dur_str = f"{int(h)} Std." if h == int(h) else f"{h:g} Std."

            # Format date range with weekday
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
        except (ValueError, KeyError, TypeError) as e:
            logger.debug(f"Skipping malformed absence entry: {e}")

    # Column Widths (A4 Width ~ 450-500 printable)
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
    except Exception as exc:
        logger.error(f"PDF export failed (absences): {exc}")
        console.print(f"[error]Fehler beim Erstellen des PDF: {exc}[/error]")
        return False
