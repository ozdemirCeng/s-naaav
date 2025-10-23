"""
Öğrenci Yükleme (Student Upload) View
Professional interface for uploading and managing students from Excel
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QFileDialog, QMessageBox, QGroupBox, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from models.database import db
from models.ogrenci_model import OgrenciModel
from controllers.ogrenci_controller import OgrenciController
from utils.excel_parser import ExcelParser

logger = logging.getLogger(__name__)


class OgrenciLoadThread(QThread):
    """Thread for loading student Excel file"""
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        try:
            parser = ExcelParser()
            ogrenciler = parser.parse_ogrenci_listesi(self.file_path)
            self.finished.emit(ogrenciler)
        except Exception as e:
            self.error.emit(str(e))


class OgrenciYukleView(QWidget):
    """Student upload and management view"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id', 1)
        
        self.ogrenci_model = OgrenciModel(db)
        self.ogrenci_controller = OgrenciController(self.ogrenci_model)
        
        self.pending_ogrenciler = []
        
        self.setup_ui()
        self.load_existing_ogrenciler()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Öğrenci Listesi Yönetimi 👥")
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
        
        info_text = QLabel(
            "Excel dosyası şu sütunları içermelidir:\n"
            "• Öğrenci No (örn: 210101001)\n"
            "• Ad Soyad (örn: Ahmet Yılmaz)\n"
            "• Sınıf (örn: 2)\n"
            "• E-posta (opsiyonel)"
        )
        info_text.setStyleSheet("color: #6b7280; font-size: 12px;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_card)
        
        # Search
        search_container = QFrame()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(16, 12, 16, 12)
        
        search_label = QLabel("🔍 Ara:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Öğrenci no veya ad ile ara...")
        self.search_input.textChanged.connect(self.filter_table)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        
        layout.addWidget(search_container)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Öğrenci No", "Ad Soyad", "Sınıf", "E-posta", "Durum"
        ])
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(4, 100)
        
        layout.addWidget(self.table)
        
        # Stats
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Segoe UI", 10))
        self.stats_label.setStyleSheet("color: #6b7280; padding: 8px;")
        layout.addWidget(self.stats_label)
    
    def load_existing_ogrenciler(self):
        """Load existing students"""
        try:
            ogrenciler = self.ogrenci_model.get_ogrenciler_by_bolum(self.bolum_id)
            self.populate_table(ogrenciler, existing=True)
            self.update_stats(len(ogrenciler), 0)
        except Exception as e:
            logger.error(f"Error loading students: {e}")
            QMessageBox.critical(self, "Hata", f"Öğrenciler yüklenirken hata oluştu:\n{str(e)}")
    
    def populate_table(self, ogrenciler, existing=False):
        """Populate table with student data"""
        self.table.setRowCount(0)
        
        for row, ogrenci in enumerate(ogrenciler):
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(ogrenci.get('ogrenci_no', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(str(ogrenci.get('ad_soyad', ''))))
            
            sinif_item = QTableWidgetItem(str(ogrenci.get('sinif', '')))
            sinif_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, sinif_item)
            
            self.table.setItem(row, 3, QTableWidgetItem(str(ogrenci.get('email', '-'))))
            
            durum = "✅ Kayıtlı" if existing else "⏳ Beklemede"
            durum_item = QTableWidgetItem(durum)
            durum_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, durum_item)
    
    def filter_table(self):
        """Filter table based on search"""
        search_text = self.search_input.text().lower()
        
        for row in range(self.table.rowCount()):
            no = self.table.item(row, 0).text().lower()
            ad = self.table.item(row, 1).text().lower()
            
            if search_text in no or search_text in ad:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)
    
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
        self.thread = OgrenciLoadThread(file_path)
        self.thread.finished.connect(self.on_excel_loaded)
        self.thread.error.connect(self.on_excel_error)
        self.thread.start()
    
    def on_excel_loaded(self, ogrenciler):
        """Handle loaded Excel data"""
        if not ogrenciler:
            QMessageBox.warning(self, "Uyarı", "Excel dosyasında öğrenci bulunamadı!")
            return
        
        self.pending_ogrenciler = ogrenciler
        self.populate_table(ogrenciler, existing=False)
        self.update_stats(0, len(ogrenciler))
        
        reply = QMessageBox.question(
            self,
            "Öğrencileri Kaydet",
            f"{len(ogrenciler)} öğrenci yüklendi. Veritabanına kaydetmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.save_ogrenciler()
    
    def on_excel_error(self, error_msg):
        """Handle Excel loading error"""
        QMessageBox.critical(self, "Hata", f"Excel dosyası yüklenirken hata oluştu:\n{error_msg}")
    
    def save_ogrenciler(self):
        """Save students to database"""
        if not self.pending_ogrenciler:
            return
        
        try:
            success_count = 0
            error_count = 0
            
            for ogrenci in self.pending_ogrenciler:
                ogrenci['bolum_id'] = self.bolum_id
                result = self.ogrenci_controller.create_ogrenci(ogrenci)
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    logger.warning(f"Failed to save student: {ogrenci['ogrenci_no']} - {result['message']}")
            
            QMessageBox.information(
                self,
                "İşlem Tamamlandı",
                f"✅ {success_count} öğrenci kaydedildi\n❌ {error_count} öğrenci kaydedilemedi"
            )
            
            self.pending_ogrenciler = []
            self.load_existing_ogrenciler()
            
        except Exception as e:
            logger.error(f"Error saving students: {e}")
            QMessageBox.critical(self, "Hata", f"Öğrenciler kaydedilirken hata oluştu:\n{str(e)}")
    
    def update_stats(self, existing, pending):
        """Update statistics label"""
        self.stats_label.setText(
            f"📊 Kayıtlı: {existing} | Beklemede: {pending}"
        )
