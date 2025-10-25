"""
Raporlar (Reports) View
Professional interface for generating and exporting reports
"""

import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QMessageBox, QGroupBox, QFileDialog,
    QCheckBox, QListWidget, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from models.database import db
from models.sinav_model import SinavModel
from utils.export_utils import ExportUtils

logger = logging.getLogger(__name__)


class ExportThread(QThread):
    """Thread for exporting reports"""
    finished = Signal(bool, str)
    error = Signal(str)
    
    def __init__(self, export_type, data, file_path):
        super().__init__()
        self.export_type = export_type
        self.data = data
        self.file_path = file_path
    
    def run(self):
        try:
            exporter = ExportUtils()
            
            if self.export_type == 'excel':
                success = exporter.export_to_excel(self.data, self.file_path)
            elif self.export_type == 'pdf':
                success = exporter.export_to_pdf(self.data, self.file_path)
            else:
                success = False
            
            if success:
                self.finished.emit(True, self.file_path)
            else:
                self.error.emit("Dışa aktarma başarısız!")
                
        except Exception as e:
            self.error.emit(str(e))


class RaporlarView(QWidget):
    """Reports view"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id', 1)
        
        self.sinav_model = SinavModel(db)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI with scroll"""
        # Main scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Set scroll widget
        scroll.setWidget(scroll_content)
        
        # Add scroll to main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Raporlar 📊")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addWidget(header)
        
        # Report types
        types_card = QGroupBox("Rapor Türü Seçimi")
        types_layout = QVBoxLayout(types_card)
        types_layout.setSpacing(12)
        
        self.report_types = QListWidget()
        self.report_types.addItems([
            "📅 Sınav Takvimi (Tam Dönem)",
            "🏛 Derslik Kullanım Raporu",
            "📚 Ders Bazlı Sınav Raporu",
            "👥 Öğrenci Sınav Listesi",
            "📝 Oturma Planı (Tüm Sınavlar)",
            "📈 İstatistiksel Özet Rapor"
        ])
        self.report_types.setCurrentRow(0)
        self.report_types.setMaximumHeight(180)
        
        types_layout.addWidget(self.report_types)
        
        layout.addWidget(types_card)
        
        # Export options
        export_card = QGroupBox("Dışa Aktarma Seçenekleri")
        export_layout = QVBoxLayout(export_card)
        export_layout.setSpacing(16)
        
        format_layout = QHBoxLayout()
        format_label = QLabel("Format:")
        format_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Excel (.xlsx)", "PDF (.pdf)"])
        self.format_combo.setFixedHeight(38)
        
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo, 1)
        
        export_layout.addLayout(format_layout)
        
        # Options
        options_label = QLabel("Ek Seçenekler:")
        options_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        export_layout.addWidget(options_label)
        
        self.include_stats_check = QCheckBox("İstatistikleri dahil et")
        self.include_stats_check.setChecked(True)
        
        self.include_logos_check = QCheckBox("Kurum logosunu ekle")
        self.include_logos_check.setChecked(True)
        
        self.include_signatures_check = QCheckBox("İmza alanları ekle")
        self.include_signatures_check.setChecked(False)
        
        export_layout.addWidget(self.include_stats_check)
        export_layout.addWidget(self.include_logos_check)
        export_layout.addWidget(self.include_signatures_check)
        
        layout.addWidget(export_card)
        
        # Export button
        button_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("📥 Raporu İndir")
        self.export_btn.setObjectName("primaryBtn")
        self.export_btn.setFixedHeight(44)
        self.export_btn.setFixedWidth(200)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_report)
        
        button_layout.addStretch()
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Info
        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame {
                background: #eff6ff;
                border: 1px solid #dbeafe;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        info_layout = QVBoxLayout(info_card)
        
        info_icon = QLabel("ℹ️ Bilgi")
        info_icon.setFont(QFont("Segoe UI", 12, QFont.Bold))
        info_icon.setStyleSheet("color: #2563eb;")
        
        info_text = QLabel(
            "• Raporlar otomatik olarak oluşturulur ve kaydedilir\n"
            "• Excel formatı düzenlenebilir tablolar içerir\n"
            "• PDF formatı yazdırılmaya hazır belgeler sunar\n"
            "• Tüm raporlar tarih-saat damgası ile oluşturulur"
        )
        info_text.setStyleSheet("color: #1e40af; font-size: 12px;")
        info_text.setWordWrap(True)
        
        info_layout.addWidget(info_icon)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_card)
        layout.addStretch()
    
    def export_report(self):
        """Export selected report"""
        report_index = self.report_types.currentRow()
        if report_index < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir rapor türü seçin!")
            return
        
        # Get format
        is_excel = self.format_combo.currentIndex() == 0
        extension = "xlsx" if is_excel else "pdf"
        filter_text = "Excel Files (*.xlsx)" if is_excel else "PDF Files (*.pdf)"
        
        # Get save location
        default_name = f"rapor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Raporu Kaydet",
            default_name,
            filter_text
        )
        
        if not file_path:
            return
        
        try:
            # Prepare data based on report type
            data = self.prepare_report_data(report_index)
            
            if not data:
                QMessageBox.warning(self, "Uyarı", "Rapor için veri bulunamadı!")
                return
            
            # Add export options
            data['options'] = {
                'include_stats': self.include_stats_check.isChecked(),
                'include_logos': self.include_logos_check.isChecked(),
                'include_signatures': self.include_signatures_check.isChecked()
            }
            
            # Export in thread
            export_type = 'excel' if is_excel else 'pdf'
            self.export_thread = ExportThread(export_type, data, file_path)
            self.export_thread.finished.connect(self.on_export_finished)
            self.export_thread.error.connect(self.on_export_error)
            
            self.export_btn.setEnabled(False)
            self.export_btn.setText("📥 İndiriliyor...")
            
            self.export_thread.start()
            
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            QMessageBox.critical(self, "Hata", f"Rapor oluşturulurken hata oluştu:\n{str(e)}")
    
    def prepare_report_data(self, report_index):
        """Prepare data for selected report type"""
        try:
            report_types = [
                'sinav_takvimi',
                'derslik_kullanimi',
                'ders_bazli',
                'ogrenci_listesi',
                'oturma_plani',
                'istatistikler'
            ]
            
            report_type = report_types[report_index]
            
            # Get data from database
            if report_type == 'sinav_takvimi':
                return self.get_sinav_takvimi_data()
            elif report_type == 'derslik_kullanimi':
                return self.get_derslik_kullanimi_data()
            elif report_type == 'ders_bazli':
                return self.get_ders_bazli_data()
            elif report_type == 'ogrenci_listesi':
                return self.get_ogrenci_listesi_data()
            elif report_type == 'oturma_plani':
                return self.get_oturma_plani_data()
            elif report_type == 'istatistikler':
                return self.get_istatistikler_data()
            
            return None
            
        except Exception as e:
            logger.error(f"Error preparing report data: {e}")
            return None
    
    def get_sinav_takvimi_data(self):
        """Get exam schedule data"""
        try:
            # First get department and exam type info
            info_query = """
                SELECT DISTINCT 
                    b.bolum_adi,
                    sp.sinav_tipi
                FROM sinav_programi sp
                JOIN bolumler b ON sp.bolum_id = b.bolum_id
                WHERE sp.bolum_id = %s
                LIMIT 1
            """
            info_result = db.execute_query(info_query, (self.bolum_id,))
            
            if not info_result:
                return None
            
            bolum_adi = info_result[0].get('bolum_adi', 'Bölüm')
            sinav_tipi = info_result[0].get('sinav_tipi', 'Sınav')
            
            # Get all exams for this department via program
            query = """
                SELECT 
                    s.sinav_id,
                    (s.tarih || ' ' || s.baslangic_saati)::timestamp as tarih_saat,
                    sp.sinav_tipi,
                    d.ders_kodu,
                    d.ders_adi,
                    d.ogretim_elemani,
                    STRING_AGG(DISTINCT dr.derslik_adi, '-' ORDER BY dr.derslik_adi) as derslikler,
                    s.ogrenci_sayisi
                FROM sinavlar s
                JOIN sinav_programi sp ON s.program_id = sp.program_id
                JOIN dersler d ON s.ders_id = d.ders_id
                LEFT JOIN sinav_derslikleri sd ON s.sinav_id = sd.sinav_id
                LEFT JOIN derslikler dr ON sd.derslik_id = dr.derslik_id
                WHERE sp.bolum_id = %s
                GROUP BY s.sinav_id, s.tarih, s.baslangic_saati, sp.sinav_tipi, 
                         d.ders_kodu, d.ders_adi, d.ogretim_elemani, s.ogrenci_sayisi
                ORDER BY s.tarih, s.baslangic_saati
            """
            
            results = db.execute_query(query, (self.bolum_id,))
            
            if not results:
                return None
            
            return {
                'type': 'sinav_takvimi',
                'title': 'Sınav Programı',
                'bolum_adi': bolum_adi,
                'sinav_tipi': sinav_tipi,
                'data': results,
                'bolum_id': self.bolum_id
            }
            
        except Exception as e:
            logger.error(f"Error getting exam schedule data: {e}")
            return None
    
    def get_derslik_kullanimi_data(self):
        """Get classroom usage data"""
        # Placeholder - implement based on your needs
        return {
            'type': 'derslik_kullanimi',
            'title': 'Derslik Kullanım Raporu',
            'data': [],
            'bolum_id': self.bolum_id
        }
    
    def get_ders_bazli_data(self):
        """Get course-based data"""
        return {
            'type': 'ders_bazli',
            'title': 'Ders Bazlı Sınav Raporu',
            'data': [],
            'bolum_id': self.bolum_id
        }
    
    def get_ogrenci_listesi_data(self):
        """Get student list data"""
        return {
            'type': 'ogrenci_listesi',
            'title': 'Öğrenci Sınav Listesi',
            'data': [],
            'bolum_id': self.bolum_id
        }
    
    def get_oturma_plani_data(self):
        """Get seating plan data"""
        return {
            'type': 'oturma_plani',
            'title': 'Oturma Planı',
            'data': [],
            'bolum_id': self.bolum_id
        }
    
    def get_istatistikler_data(self):
        """Get statistics data"""
        return {
            'type': 'istatistikler',
            'title': 'İstatistiksel Özet Rapor',
            'data': [],
            'bolum_id': self.bolum_id
        }
    
    def on_export_finished(self, success, file_path):
        """Handle export completion"""
        self.export_btn.setEnabled(True)
        self.export_btn.setText("📥 Raporu İndir")
        
        if success:
            QMessageBox.information(
                self,
                "Başarılı",
                f"✅ Rapor başarıyla kaydedildi:\n\n{file_path}"
            )
        else:
            QMessageBox.warning(self, "Uyarı", "Rapor kaydedilemedi!")
    
    def on_export_error(self, error_msg):
        """Handle export error"""
        self.export_btn.setEnabled(True)
        self.export_btn.setText("📥 Raporu İndir")
        
        QMessageBox.critical(self, "Hata", f"Rapor oluşturulurken hata oluştu:\n{error_msg}")
