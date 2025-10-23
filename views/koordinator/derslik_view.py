"""
Derslik (Classroom) Management View
Professional interface for managing classrooms
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QSpinBox, QDialog, QFormLayout, QMessageBox,
    QGroupBox, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models.database import db
from models.derslik_model import DerslikModel
from controllers.derslik_controller import DerslikController

logger = logging.getLogger(__name__)


class DerslikDialog(QDialog):
    """Dialog for adding/editing classroom"""
    
    def __init__(self, parent=None, derslik_data=None, bolum_id=None):
        super().__init__(parent)
        self.derslik_data = derslik_data
        self.bolum_id = bolum_id
        self.is_edit_mode = derslik_data is not None
        
        self.setWindowTitle("Derslik Düzenle" if self.is_edit_mode else "Yeni Derslik Ekle")
        self.setMinimumWidth(500)
        self.setup_ui()
        
        if self.is_edit_mode:
            self.load_derslik_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Derslik Düzenle" if self.is_edit_mode else "Yeni Derslik Ekle")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Form
        form_group = QGroupBox("Derslik Bilgileri")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
        
        self.kod_input = QLineEdit()
        self.kod_input.setPlaceholderText("örn: A101")
        form_layout.addRow("Derslik Kodu:", self.kod_input)
        
        self.ad_input = QLineEdit()
        self.ad_input.setPlaceholderText("örn: Amfi A101")
        form_layout.addRow("Derslik Adı:", self.ad_input)
        
        self.kapasite_input = QSpinBox()
        self.kapasite_input.setMinimum(1)
        self.kapasite_input.setMaximum(500)
        self.kapasite_input.setValue(30)
        form_layout.addRow("Kapasite:", self.kapasite_input)
        
        self.satir_input = QSpinBox()
        self.satir_input.setMinimum(1)
        self.satir_input.setMaximum(50)
        self.satir_input.setValue(5)
        self.satir_input.valueChanged.connect(self.update_kapasite_hint)
        form_layout.addRow("Satır Sayısı:", self.satir_input)
        
        self.sutun_input = QSpinBox()
        self.sutun_input.setMinimum(1)
        self.sutun_input.setMaximum(50)
        self.sutun_input.setValue(6)
        self.sutun_input.valueChanged.connect(self.update_kapasite_hint)
        form_layout.addRow("Sütun Sayısı:", self.sutun_input)
        
        self.sira_yapisi_input = QSpinBox()
        self.sira_yapisi_input.setMinimum(1)
        self.sira_yapisi_input.setMaximum(10)
        self.sira_yapisi_input.setValue(2)
        form_layout.addRow("Sıra Yapısı:", self.sira_yapisi_input)
        
        # Kapasite hint
        self.kapasite_hint = QLabel()
        self.kapasite_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        form_layout.addRow("", self.kapasite_hint)
        self.update_kapasite_hint()
        
        layout.addWidget(form_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("İptal")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Kaydet")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def update_kapasite_hint(self):
        """Update capacity hint based on rows/columns"""
        total = self.satir_input.value() * self.sutun_input.value()
        self.kapasite_hint.setText(f"Maksimum kapasite: {total} (satır × sütun)")
    
    def load_derslik_data(self):
        """Load classroom data for editing"""
        if self.derslik_data:
            self.kod_input.setText(str(self.derslik_data.get('derslik_kodu', '')))
            self.ad_input.setText(str(self.derslik_data.get('derslik_adi', '')))
            self.kapasite_input.setValue(int(self.derslik_data.get('kapasite', 30)))
            self.satir_input.setValue(int(self.derslik_data.get('satir_sayisi', 5)))
            self.sutun_input.setValue(int(self.derslik_data.get('sutun_sayisi', 6)))
            self.sira_yapisi_input.setValue(int(self.derslik_data.get('sira_yapisi', 2)))
    
    def get_derslik_data(self):
        """Get classroom data from form"""
        return {
            'bolum_id': self.bolum_id,
            'derslik_kodu': self.kod_input.text().strip(),
            'derslik_adi': self.ad_input.text().strip(),
            'kapasite': self.kapasite_input.value(),
            'satir_sayisi': self.satir_input.value(),
            'sutun_sayisi': self.sutun_input.value(),
            'sira_yapisi': self.sira_yapisi_input.value()
        }
    
    def validate(self):
        """Validate form data"""
        if not self.kod_input.text().strip():
            QMessageBox.warning(self, "Uyarı", "Derslik kodu boş olamaz!")
            return False
        
        if not self.ad_input.text().strip():
            QMessageBox.warning(self, "Uyarı", "Derslik adı boş olamaz!")
            return False
        
        max_kapasite = self.satir_input.value() * self.sutun_input.value()
        if self.kapasite_input.value() > max_kapasite:
            QMessageBox.warning(
                self, 
                "Uyarı", 
                f"Kapasite, satır×sütun ({max_kapasite}) değerinden büyük olamaz!"
            )
            return False
        
        return True
    
    def accept(self):
        """Accept dialog if validation passes"""
        if self.validate():
            super().accept()


class DerslikView(QWidget):
    """Classroom management view"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id', 1)
        
        self.derslik_model = DerslikModel(db)
        self.derslik_controller = DerslikController(self.derslik_model)
        
        self.setup_ui()
        self.load_derslikler()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Derslik Yönetimi 🏛")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        
        add_btn = QPushButton("+ Yeni Derslik Ekle")
        add_btn.setObjectName("primaryBtn")
        add_btn.setFixedHeight(40)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.add_derslik)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(add_btn)
        
        layout.addWidget(header)
        
        # Search bar
        search_container = QFrame()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(16, 12, 16, 12)
        
        search_label = QLabel("🔍 Ara:")
        search_label.setFont(QFont("Segoe UI", 11))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Derslik kodu veya adı ile ara...")
        self.search_input.textChanged.connect(self.filter_table)
        self.search_input.setFixedHeight(38)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        
        layout.addWidget(search_container)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Kod", "Derslik Adı", "Kapasite", 
            "Satır", "Sütun", "Sıra Yapısı", "İşlemler"
        ])
        
        # Table styling
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        
        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        
        self.table.setColumnWidth(0, 60)   # ID
        self.table.setColumnWidth(1, 100)  # Kod
        self.table.setColumnWidth(3, 80)   # Kapasite
        self.table.setColumnWidth(4, 60)   # Satır
        self.table.setColumnWidth(5, 60)   # Sütun
        self.table.setColumnWidth(6, 100)  # Sıra Yapısı
        self.table.setColumnWidth(7, 180)  # İşlemler
        
        layout.addWidget(self.table)
        
        # Stats footer
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Segoe UI", 10))
        self.stats_label.setStyleSheet("color: #6b7280; padding: 8px;")
        layout.addWidget(self.stats_label)
    
    def load_derslikler(self):
        """Load classrooms from database"""
        try:
            derslikler = self.derslik_model.get_derslikler_by_bolum(self.bolum_id)
            self.populate_table(derslikler)
            self.update_stats(len(derslikler))
        except Exception as e:
            logger.error(f"Error loading classrooms: {e}")
            QMessageBox.critical(self, "Hata", f"Derslikler yüklenirken hata oluştu:\n{str(e)}")
    
    def populate_table(self, derslikler):
        """Populate table with classroom data"""
        self.table.setRowCount(0)
        
        for row, derslik in enumerate(derslikler):
            self.table.insertRow(row)
            
            # ID
            id_item = QTableWidgetItem(str(derslik['derslik_id']))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, id_item)
            
            # Kod
            kod_item = QTableWidgetItem(str(derslik['derslik_kodu']))
            kod_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, kod_item)
            
            # Ad
            self.table.setItem(row, 2, QTableWidgetItem(str(derslik['derslik_adi'])))
            
            # Kapasite
            kap_item = QTableWidgetItem(str(derslik['kapasite']))
            kap_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, kap_item)
            
            # Satır
            satir_item = QTableWidgetItem(str(derslik['satir_sayisi']))
            satir_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, satir_item)
            
            # Sütun
            sutun_item = QTableWidgetItem(str(derslik['sutun_sayisi']))
            sutun_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, sutun_item)
            
            # Sıra Yapısı
            sira_item = QTableWidgetItem(str(derslik['sira_yapisi']))
            sira_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 6, sira_item)
            
            # Action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(8)
            
            edit_btn = QPushButton("✏️ Düzenle")
            edit_btn.setFixedHeight(32)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, d=derslik: self.edit_derslik(d))
            
            delete_btn = QPushButton("🗑️ Sil")
            delete_btn.setObjectName("dangerBtn")
            delete_btn.setFixedHeight(32)
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.clicked.connect(lambda checked, d=derslik: self.delete_derslik(d))
            
            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)
            
            self.table.setCellWidget(row, 7, action_widget)
    
    def filter_table(self):
        """Filter table based on search text"""
        search_text = self.search_input.text().lower()
        
        for row in range(self.table.rowCount()):
            kod = self.table.item(row, 1).text().lower()
            ad = self.table.item(row, 2).text().lower()
            
            if search_text in kod or search_text in ad:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)
    
    def update_stats(self, count):
        """Update statistics label"""
        self.stats_label.setText(f"📊 Toplam {count} derslik kayıtlı")
    
    def add_derslik(self):
        """Add new classroom"""
        dialog = DerslikDialog(self, bolum_id=self.bolum_id)
        if dialog.exec():
            derslik_data = dialog.get_derslik_data()
            
            try:
                result = self.derslik_controller.create_derslik(derslik_data)
                if result['success']:
                    QMessageBox.information(self, "Başarılı", result['message'])
                    self.load_derslikler()
                else:
                    QMessageBox.warning(self, "Hata", result['message'])
            except Exception as e:
                logger.error(f"Error adding classroom: {e}")
                QMessageBox.critical(self, "Hata", f"Derslik eklenirken hata oluştu:\n{str(e)}")
    
    def edit_derslik(self, derslik):
        """Edit classroom"""
        dialog = DerslikDialog(self, derslik_data=derslik, bolum_id=self.bolum_id)
        if dialog.exec():
            derslik_data = dialog.get_derslik_data()
            
            try:
                result = self.derslik_controller.update_derslik(derslik['derslik_id'], derslik_data)
                if result['success']:
                    QMessageBox.information(self, "Başarılı", result['message'])
                    self.load_derslikler()
                else:
                    QMessageBox.warning(self, "Hata", result['message'])
            except Exception as e:
                logger.error(f"Error updating classroom: {e}")
                QMessageBox.critical(self, "Hata", f"Derslik güncellenirken hata oluştu:\n{str(e)}")
    
    def delete_derslik(self, derslik):
        """Delete classroom"""
        reply = QMessageBox.question(
            self,
            "Derslik Sil",
            f"'{derslik['derslik_adi']}' dersliğini silmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                result = self.derslik_controller.delete_derslik(derslik['derslik_id'])
                if result['success']:
                    QMessageBox.information(self, "Başarılı", result['message'])
                    self.load_derslikler()
                else:
                    QMessageBox.warning(self, "Hata", result['message'])
            except Exception as e:
                logger.error(f"Error deleting classroom: {e}")
                QMessageBox.critical(self, "Hata", f"Derslik silinirken hata oluştu:\n{str(e)}")
