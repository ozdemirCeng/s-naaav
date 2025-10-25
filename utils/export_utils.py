"""
Export Utilities
Export data to Excel and PDF formats
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os

logger = logging.getLogger(__name__)


class ExportUtils:
    """Data export utilities"""
    
    @staticmethod
    def export_to_excel(data: Dict, file_path: str) -> bool:
        """Export data to Excel file with professional formatting"""
        try:
            report_type = data.get('type', 'generic')
            title = data.get('title', 'Rapor')
            records = data.get('data', [])
            
            if not records:
                logger.warning("No data to export")
                return False
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Sınav Programı"
            
            schedule_by_datetime = defaultdict(list)
            for sinav in records:
                if isinstance(sinav.get('tarih_saat'), str):
                    tarih = datetime.fromisoformat(sinav['tarih_saat'])
                else:
                    tarih = sinav['tarih_saat']
                datetime_key = (tarih.date(), tarih.time())
                schedule_by_datetime[datetime_key].append(sinav)
            
            sorted_datetimes = sorted(schedule_by_datetime.keys())
            
            # Get department and exam type info
            bolum_adi = data.get('bolum_adi', '')
            sinav_tipi = data.get('sinav_tipi', '')
            
            # Create title with department and exam type
            full_title = f"{bolum_adi} {sinav_tipi} {title}".upper()
            
            ws.merge_cells('A1:E1')
            title_cell = ws['A1']
            title_cell.value = full_title
            title_cell.font = Font(size=14, bold=True, color="FFFFFF")
            title_cell.fill = PatternFill(start_color="E67E22", end_color="E67E22", fill_type="solid")
            title_cell.alignment = Alignment(horizontal='center', vertical='center')
            ws.row_dimensions[1].height = 25
            
            # Add THICK BLACK border below title
            thick_black_bottom = Border(bottom=Side(style='thick', color='000000'))
            for col in range(1, 6):
                cell = ws.cell(row=1, column=col)
                cell.border = Border(
                    top=cell.border.top,
                    left=cell.border.left,
                    right=cell.border.right,
                    bottom=Side(style='thick', color='000000')
                )
            
            headers = ['Tarih', 'Sınav Saati', 'Ders Adı', 'Öğretim Elemanı', 'Derslik']
            ws.append(headers)
            
            header_fill = PatternFill(start_color="E67E22", end_color="E67E22", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=11)
            
            for cell in ws[2]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            ws.row_dimensions[2].height = 20
            
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            current_row = 3
            date_merge_start = {}
            
            for datetime_key in sorted_datetimes:
                date_obj, time_obj = datetime_key
                exams_at_this_time = schedule_by_datetime[datetime_key]
                
                date_str = date_obj.strftime('%d.%m.%Y')
                time_str = time_obj.strftime('%H.%M')
                
                if date_str not in date_merge_start:
                    date_merge_start[date_str] = current_row
                
                for exam in exams_at_this_time:
                    ders_adi = exam.get('ders_adi', '')
                    ogretim_elemani = exam.get('ogretim_elemani', '')
                    derslik = exam.get('derslikler', exam.get('derslik_adi', ''))
                    
                    ws.append([date_str, time_str, ders_adi, ogretim_elemani, derslik])
                    
                    for col in range(1, 6):
                        cell = ws.cell(row=current_row, column=col)
                        cell.border = thin_border
                        cell.alignment = Alignment(
                            horizontal='center' if col in [1, 2, 5] else 'left',
                            vertical='center',
                            wrap_text=True
                        )
                    
                    current_row += 1
            
            for date_str, start_row in date_merge_start.items():
                end_row = start_row
                for row in range(start_row, current_row):
                    if ws.cell(row=row, column=1).value == date_str:
                        end_row = row
                
                if end_row > start_row:
                    ws.merge_cells(f'A{start_row}:A{end_row}')
                    merged_cell = ws.cell(row=start_row, column=1)
                    merged_cell.alignment = Alignment(horizontal='center', vertical='center')
                    merged_cell.fill = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")
                    merged_cell.font = Font(bold=True)
            
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 12
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 25
            ws.column_dimensions['E'].width = 20
            
            # Add THICK BLACK borders around entire table
            thick_border = Side(style='thick', color='000000')
            
            for row in range(1, current_row):
                for col in range(1, 6):
                    cell = ws.cell(row=row, column=col)
                    current_border = cell.border
                    
                    # Determine which borders should be thick
                    top = thick_border if row == 1 else current_border.top
                    bottom = thick_border if row == current_row - 1 else current_border.bottom
                    left = thick_border if col == 1 else current_border.left
                    right = thick_border if col == 5 else current_border.right
                    
                    cell.border = Border(top=top, bottom=bottom, left=left, right=right)
            
            wb.save(file_path)
            logger.info(f"Excel exported: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Excel export error: {e}", exc_info=True)
            return False
    
    @staticmethod
    def export_to_pdf(data: Dict, file_path: str) -> bool:
        """Export data to PDF file with Turkish character support and merged date cells using ReportLab"""
        try:
            title = data.get('title', 'Rapor')
            records = data.get('data', [])
            options = data.get('options', {})
            
            if not records:
                logger.warning("No data to export")
                return False
            
            # Register Turkish font - try Arial first (Windows), then DejaVu
            font_registered = False
            font_name = 'TurkishFont'
            font_name_bold = 'TurkishFont-Bold'
            
            try:
                # Try Arial first (Windows default, supports Turkish)
                arial_paths = {
                    'regular': [
                        'C:/Windows/Fonts/arial.ttf',
                        'C:/Windows/Fonts/Arial.ttf',
                    ],
                    'bold': [
                        'C:/Windows/Fonts/arialbd.ttf',
                        'C:/Windows/Fonts/Arialbd.ttf',
                    ]
                }
                
                # Try to register Arial
                for font_path in arial_paths['regular']:
                    if os.path.exists(font_path):
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        font_registered = True
                        logger.info(f"Registered Arial font from: {font_path}")
                        break
                
                if font_registered:
                    for font_path in arial_paths['bold']:
                        if os.path.exists(font_path):
                            pdfmetrics.registerFont(TTFont(font_name_bold, font_path))
                            logger.info(f"Registered Arial Bold font from: {font_path}")
                            break
                
                # If Arial not found, try DejaVu
                if not font_registered:
                    dejavu_paths = {
                        'regular': [
                            'C:/Windows/Fonts/DejaVuSans.ttf',
                            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                        ],
                        'bold': [
                            'C:/Windows/Fonts/DejaVuSans-Bold.ttf',
                            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                        ]
                    }
                    
                    for font_path in dejavu_paths['regular']:
                        if os.path.exists(font_path):
                            pdfmetrics.registerFont(TTFont(font_name, font_path))
                            font_registered = True
                            logger.info(f"Registered DejaVu font from: {font_path}")
                            break
                    
                    if font_registered:
                        for font_path in dejavu_paths['bold']:
                            if os.path.exists(font_path):
                                pdfmetrics.registerFont(TTFont(font_name_bold, font_path))
                                logger.info(f"Registered DejaVu Bold font from: {font_path}")
                                break
                
                if not font_registered:
                    logger.warning("No Turkish-compatible font found, using Helvetica")
            except Exception as e:
                logger.error(f"Font registration failed: {e}")
                font_registered = False
            
            # Group by date and time
            schedule_by_datetime = defaultdict(list)
            for sinav in records:
                if isinstance(sinav.get('tarih_saat'), str):
                    tarih = datetime.fromisoformat(sinav['tarih_saat'])
                else:
                    tarih = sinav['tarih_saat']
                datetime_key = (tarih.date(), tarih.time())
                schedule_by_datetime[datetime_key].append(sinav)
            
            sorted_datetimes = sorted(schedule_by_datetime.keys())
            
            # Build table data with row span info for both date and time
            table_data = []
            table_data.append(['Tarih', 'Sınav Saati', 'Ders Adı', 'Öğretim Elemanı', 'Derslik'])
            
            date_spans = []  # (start_row, end_row) for date merging
            time_spans = []  # (start_row, end_row) for time merging
            current_date = None
            current_time = None
            date_start_row = 1  # Start after header
            time_start_row = 1
            
            for datetime_key in sorted_datetimes:
                date_obj, time_obj = datetime_key
                exams_at_this_time = schedule_by_datetime[datetime_key]
                
                date_str = date_obj.strftime('%d.%m.%Y')
                time_str = time_obj.strftime('%H:%M')
                
                # Track date changes
                if current_date != date_str:
                    if current_date is not None:
                        date_spans.append((date_start_row, len(table_data) - 1))
                    current_date = date_str
                    date_start_row = len(table_data)
                
                # Track time changes (for same date)
                datetime_str = f"{date_str}_{time_str}"
                if current_time != datetime_str:
                    if current_time is not None and time_start_row < len(table_data):
                        time_spans.append((time_start_row, len(table_data) - 1))
                    current_time = datetime_str
                    time_start_row = len(table_data)
                
                for exam in exams_at_this_time:
                    ders_adi = exam.get('ders_adi', '')
                    ogretim_elemani = exam.get('ogretim_elemani', '')
                    derslik = exam.get('derslikler', exam.get('derslik_adi', ''))
                    
                    table_data.append([date_str, time_str, ders_adi, ogretim_elemani, derslik if derslik else ''])
            
            # Add last spans
            if current_date is not None:
                date_spans.append((date_start_row, len(table_data) - 1))
            if current_time is not None and time_start_row < len(table_data):
                time_spans.append((time_start_row, len(table_data) - 1))
            
            # Create PDF with CUSTOM EXTENDED landscape page - EXTRA LONG for single page
            # Custom page size: A4 width (29.7cm) x EXTENDED height (35cm) - landscape orientation
            custom_pagesize = (35*cm, 29.7*cm)  # (width, height) in landscape
            
            doc = SimpleDocTemplate(
                file_path,
                pagesize=custom_pagesize,
                topMargin=0.5*cm,
                bottomMargin=0.5*cm,
                leftMargin=0.8*cm,
                rightMargin=0.8*cm
            )
            
            elements = []
            
            # Get department and exam type info
            bolum_adi = data.get('bolum_adi', '')
            sinav_tipi = data.get('sinav_tipi', '')
            
            # Create title with department and exam type
            full_title = f"{bolum_adi} {sinav_tipi} {title}".upper()
            
            # Title - MINIMAL with BLACK text
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=getSampleStyleSheet()['Heading1'],
                fontSize=11,
                textColor=colors.black,
                spaceAfter=2,
                alignment=TA_CENTER,
                fontName=font_name_bold if font_registered else 'Helvetica-Bold'
            )
            
            elements.append(Paragraph(full_title, title_style))
            elements.append(Spacer(1, 0.15*cm))
            
            # Date info - MINIMAL
            date_style = ParagraphStyle(
                'DateStyle',
                parent=getSampleStyleSheet()['Normal'],
                fontSize=6.5,
                alignment=TA_CENTER,
                fontName=font_name if font_registered else 'Helvetica'
            )
            date_text = f"Olusturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            elements.append(Paragraph(date_text, date_style))
            elements.append(Spacer(1, 0.15*cm))
            
            # Create table with adjusted column widths for EXTENDED landscape page
            # Total width: ~33.4cm for extended page (35cm - 1.6cm margins)
            table = Table(table_data, colWidths=[2.8*cm, 2.8*cm, 16*cm, 8.5*cm, 3.3*cm], 
                         repeatRows=1)  # Repeat header on each page
            
            # Base table style - COMPACT but readable with THICK outer borders
            table_style = TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E67E22')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), font_name_bold if font_registered else 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                
                # All cells - COMPACT PADDING for maximum rows
                ('FONTNAME', (0, 1), (-1, -1), font_name if font_registered else 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7.5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 1), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
                
                # Alignment
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Tarih
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Saat
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Ders Adı
                ('ALIGN', (3, 1), (3, -1), 'LEFT'),    # Öğretim Elemanı
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Derslik
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (1, 1), (-1, -1), [colors.white, colors.HexColor('#F8F8F8')]),
                
                # THICK BLACK outer borders for entire table
                ('BOX', (0, 0), (-1, -1), 2.5, colors.black),
            ])
            
            # Add date cell merging (SPAN) with THICK BLACK borders for separation
            for start_row, end_row in date_spans:
                if end_row > start_row:
                    table_style.add('SPAN', (0, start_row), (0, end_row))
                    table_style.add('BACKGROUND', (0, start_row), (0, end_row), colors.HexColor('#F0F0F0'))
                    table_style.add('FONTNAME', (0, start_row), (0, end_row), 
                                  font_name_bold if font_registered else 'Helvetica-Bold')
                    # Add THICK BLACK borders around date groups for clear separation
                    table_style.add('LINEABOVE', (0, start_row), (-1, start_row), 2.5, colors.black)
                    table_style.add('LINEBELOW', (0, end_row), (-1, end_row), 2.5, colors.black)
            
            # Add time cell merging (SPAN)
            for start_row, end_row in time_spans:
                if end_row > start_row:
                    table_style.add('SPAN', (1, start_row), (1, end_row))
                    table_style.add('BACKGROUND', (1, start_row), (1, end_row), colors.HexColor('#F8F8F8'))
                    table_style.add('FONTNAME', (1, start_row), (1, end_row), 
                                  font_name_bold if font_registered else 'Helvetica-Bold')
            
            table.setStyle(table_style)
            elements.append(table)
            
            # Build PDF
            doc.build(elements)
            
            logger.info(f"PDF exported: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"PDF export error: {e}", exc_info=True)
            return False
    
    @staticmethod
    def export_seating_plan(sinav_data: Dict, oturma_data: List[Dict], file_path: str) -> bool:
        """Export seating plan to PDF"""
        data = {
            'type': 'oturma_plani',
            'title': f"Oturma Planı - {sinav_data.get('ders_kodu', '')}",
            'data': oturma_data,
            'options': {'include_signatures': True}
        }
        
        return ExportUtils.export_to_pdf(data, file_path)

