"""
Ders Yükleme (Course Upload) View
Professional interface for uploading and managing courses from Excel
"""

import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from models.database import db
from models.ders_model import DersModel
from controllers.ders_controller import DersController
from utils.excel_parser import ExcelParser

logger = logging.getLogger(__name__)


class ExcelLoadThread(QThread):
    """Thread for loading Excel file"""
    progress = Signal(int)
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        try:
            parser = ExcelParser()
            dersler = parser.parse_ders_listesi(self.file_path)
            self.finished.emit(dersler)
        except Exception as e:
            self.error.emit(str(e))


class DersYukleView(QWidget):
    """Course upload and management view"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id', 1)
        
        self.ders_model = DersModel(db)
        self.ders_controller = DersController(self.ders_model)
        
        self.pending_dersler = []
        
        self.setup_ui()
        self.load_existing_dersler()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Ders Listesi Yönetimi 📚")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        
        upload_btn = QPushButton("📤 Excel Yükle")
        upload_btn.setObjectName("primaryBtn")
        upload_btn.setFixedHeight(40)
        upload_btn.setCursor(Qt.PointingHandCursor)
        upload_btn.clicked.connect(self.upload_excel)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(upload_btn)
        
        layout.addWidget(header)
        
        # Info card
        info_card = QGroupBox("ℹ️ Excel Formatı")
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(8)
        
        info_text = QLabel(
            "Excel dosyası şu sütunları içermelidir:\n"
            "• Ders Kodu (örn: BMU101)\n"
            "• Ders Adı (örn: Programlamaya Giriş)\n"
            "• Kredi (örn: 3)\n"
            "• Yarıyıl (örn: 1)\n"
            "• Ders Yapısı (Zorunlu/Seçmeli)"
        )
        info_text.setStyleSheet("color: #6b7280; font-size: 12px;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_card)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Ders Kodu", "Ders Adı", "Kredi", "Yarıyıl", "Ders Yapısı", "Durum"
        ])
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 120)
        self.table.setColumnWidth(5, 100)
        
        layout.addWidget(self.table)
        
        # Stats
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Segoe UI", 10))
        self.stats_label.setStyleSheet("color: #6b7280; padding: 8px;")
        layout.addWidget(self.stats_label)
    
    def load_existing_dersler(self):
        """Load existing courses"""
        try:
            dersler = self.ders_model.get_dersler_by_bolum(self.bolum_id)
            self.populate_table(dersler, existing=True)
            self.update_stats(len(dersler), 0)
        except Exception as e:
            logger.error(f"Error loading courses: {e}")
            QMessageBox.critical(self, "Hata", f"Dersler yüklenirken hata oluştu:\n{str(e)}")
    
    def populate_table(self, dersler, existing=False):
        """Populate table with course data"""
        self.table.setRowCount(0)
        
        for row, ders in enumerate(dersler):
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(ders.get('ders_kodu', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(str(ders.get('ders_adi', ''))))
            
            kredi_item = QTableWidgetItem(str(ders.get('kredi', '')))
            kredi_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, kredi_item)
            
            yariyil_item = QTableWidgetItem(str(ders.get('yariyil', '')))
            yariyil_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, yariyil_item)
            
            yapisi_item = QTableWidgetItem(str(ders.get('ders_yapisi', '')))
            yapisi_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, yapisi_item)
            
            durum = "✅ Kayıtlı" if existing else "⏳ Beklemede"
            durum_item = QTableWidgetItem(durum)
            durum_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, durum_item)
    
    def upload_excel(self):
        """Upload Excel file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Excel Dosyası Seç",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            self.load_excel(file_path)
    
    def load_excel(self, file_path):
        """Load Excel file in background thread"""
        self.thread = ExcelLoadThread(file_path)
        self.thread.finished.connect(self.on_excel_loaded)
        self.thread.error.connect(self.on_excel_error)
        self.thread.start()
    
    def on_excel_loaded(self, dersler):
        """Handle loaded Excel data"""
        if not dersler:
            QMessageBox.warning(self, "Uyarı", "Excel dosyasında ders bulunamadı!")
            return
        
        self.pending_dersler = dersler
        self.populate_table(dersler, existing=False)
        self.update_stats(0, len(dersler))
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Dersleri Kaydet",
            f"{len(dersler)} ders yüklendi. Veritabanına kaydetmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.save_dersler()
    
    def on_excel_error(self, error_msg):
        """Handle Excel loading error"""
        QMessageBox.critical(self, "Hata", f"Excel dosyası yüklenirken hata oluştu:\n{error_msg}")
    
    def save_dersler(self):
        """Save courses to database"""
        if not self.pending_dersler:
            return
        
        try:
            success_count = 0
            error_count = 0
            
            for ders in self.pending_dersler:
                ders['bolum_id'] = self.bolum_id
                result = self.ders_controller.create_ders(ders)
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    logger.warning(f"Failed to save course: {ders['ders_kodu']} - {result['message']}")
            
            QMessageBox.information(
                self,
                "İşlem Tamamlandı",
                f"✅ {success_count} ders kaydedildi\n❌ {error_count} ders kaydedilemedi"
            )
            
            self.pending_dersler = []
            self.load_existing_dersler()
            
        except Exception as e:
            logger.error(f"Error saving courses: {e}")
            QMessageBox.critical(self, "Hata", f"Dersler kaydedilirken hata oluştu:\n{str(e)}")
    
    def update_stats(self, existing, pending):
        """Update statistics label"""
        self.stats_label.setText(
            f"📊 Kayıtlı: {existing} | Beklemede: {pending}"
        )
