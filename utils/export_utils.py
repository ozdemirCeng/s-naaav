"""
Export Utilities
Export data to Excel and PDF formats
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

logger = logging.getLogger(__name__)


class ExportUtils:
    """Data export utilities"""
    
    @staticmethod
    def export_to_excel(data: Dict, file_path: str) -> bool:
        """
        Export data to Excel file
        
        Args:
            data: Dictionary containing data and metadata
            file_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            report_type = data.get('type', 'generic')
            title = data.get('title', 'Rapor')
            records = data.get('data', [])
            
            if not records:
                logger.warning("No data to export")
                return False
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            # Create Excel writer
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Write data
                df.to_excel(writer, sheet_name='Veri', index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Veri']
                
                # Format headers
                for cell in worksheet[1]:
                    cell.font = cell.font.copy(bold=True)
                    cell.fill = cell.fill.copy(
                        start_color='00A651',
                        end_color='00A651',
                        fill_type='solid'
                    )
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info(f"✅ Excel exported: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Excel export error: {e}")
            return False
    
    @staticmethod
    def export_to_pdf(data: Dict, file_path: str) -> bool:
        """
        Export data to PDF file
        
        Args:
            data: Dictionary containing data and metadata
            file_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            title = data.get('title', 'Rapor')
            records = data.get('data', [])
            options = data.get('options', {})
            
            if not records:
                logger.warning("No data to export")
                return False
            
            # Create PDF
            doc = SimpleDocTemplate(
                file_path,
                pagesize=landscape(A4),
                topMargin=1*cm,
                bottomMargin=1*cm,
                leftMargin=1*cm,
                rightMargin=1*cm
            )
            
            # Container for elements
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            if options.get('include_logos', True):
                title_text = f"KOCAELİ ÜNİVERSİTESİ<br/>{title}"
            else:
                title_text = title
            
            title_para = Paragraph(title_text, styles['Title'])
            elements.append(title_para)
            elements.append(Spacer(1, 0.5*cm))
            
            # Date
            date_para = Paragraph(
                f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                styles['Normal']
            )
            elements.append(date_para)
            elements.append(Spacer(1, 0.5*cm))
            
            # Convert data to table
            df = pd.DataFrame(records)
            
            # Prepare table data
            table_data = [df.columns.tolist()] + df.values.tolist()
            
            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00A651')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Body
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                
                # Alternating rows
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            elements.append(table)
            
            # Signature section if requested
            if options.get('include_signatures', False):
                elements.append(Spacer(1, 1*cm))
                sig_para = Paragraph(
                    "____________________<br/>İmza",
                    styles['Normal']
                )
                elements.append(sig_para)
            
            # Build PDF
            doc.build(elements)
            
            logger.info(f"✅ PDF exported: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"PDF export error: {e}")
            return False
    
    @staticmethod
    def export_seating_plan(sinav_data: Dict, oturma_data: List[Dict], file_path: str) -> bool:
        """
        Export seating plan to PDF
        
        Args:
            sinav_data: Exam information
            oturma_data: Seating plan data
            file_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        # Simplified implementation - expand as needed
        data = {
            'type': 'oturma_plani',
            'title': f"Oturma Planı - {sinav_data.get('ders_kodu', '')}",
            'data': oturma_data,
            'options': {'include_signatures': True}
        }
        
        return ExportUtils.export_to_pdf(data, file_path)
