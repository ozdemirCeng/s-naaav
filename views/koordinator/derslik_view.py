"""
Derslik (Classroom) Management View
Organized tab-based interface with proper save functionality
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QSpinBox, QMessageBox, QGroupBox, QFormLayout, QTabWidget,
    QDialog, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from models.database import db
from models.derslik_model import DerslikModel
from controllers.derslik_controller import DerslikController

logger = logging.getLogger(__name__)


class DerslikView(QWidget):
    """Tab-based classroom management"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id', 1)
        
        self.derslik_model = DerslikModel(db)
        self.derslik_controller = DerslikController(self.derslik_model)
        
        self.selected_derslik = None
        self.form_modified = False
        
        self.setup_ui()
        self.load_derslikler()
    
    def setup_ui(self):
        """Setup tab-based UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Derslik Yönetimi 🏛")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(header)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Segoe UI", 11))
        
        # Tab 1: Derslik Listesi
        self.list_tab = self.create_list_tab()
        self.tabs.addTab(self.list_tab, "📋 Derslik Listesi")
        
        # Tab 2: Yeni Derslik Ekle
        self.add_tab = self.create_add_tab()
        self.tabs.addTab(self.add_tab, "➕ Yeni Derslik Ekle")
        
        layout.addWidget(self.tabs)
    
    def create_list_tab(self):
        """Create list and edit tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Search bar
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(16, 12, 16, 12)
        
        search_label = QLabel("🔍 Ara:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Derslik kodu veya adı ile ara...")
        self.search_input.textChanged.connect(self.filter_table)
        self.search_input.setFixedHeight(38)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_frame)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Kod", "Derslik Adı", "Kapasite", 
            "Satır", "Sütun", "Sıra Yapısı", "İşlemler"
        ])
        
        # Make table read-only
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        
        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 60)
        self.table.setColumnWidth(4, 60)
        self.table.setColumnWidth(5, 100)
        # Actions column will size to contents; keep a sensible minimum via cell widget
        
        layout.addWidget(self.table)
        
        # Stats
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Segoe UI", 10))
        self.stats_label.setStyleSheet("color: #6b7280; padding: 8px;")
        layout.addWidget(self.stats_label)
        
        # Edit section (initially hidden)
        self.edit_section = QGroupBox("✏️ Seçili Dersliği Düzenle")
        self.edit_section.setVisible(False)
        edit_layout = QVBoxLayout(self.edit_section)
        edit_layout.setSpacing(16)
        
        # Edit form
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        self.edit_kod = QLineEdit()
        self.edit_kod.textChanged.connect(self.mark_form_modified)
        form_layout.addRow("Derslik Kodu *:", self.edit_kod)
        
        self.edit_ad = QLineEdit()
        self.edit_ad.textChanged.connect(self.mark_form_modified)
        form_layout.addRow("Derslik Adı *:", self.edit_ad)
        
        kapasite_layout = QHBoxLayout()
        self.edit_kapasite = QSpinBox()
        self.edit_kapasite.setMinimum(1)
        self.edit_kapasite.setMaximum(500)
        self.edit_kapasite.setFixedWidth(100)
        self.edit_kapasite.valueChanged.connect(self.mark_form_modified)
        kapasite_layout.addWidget(self.edit_kapasite)
        kapasite_layout.addStretch()
        form_layout.addRow("Kapasite *:", kapasite_layout)
        
        satir_layout = QHBoxLayout()
        self.edit_satir = QSpinBox()
        self.edit_satir.setMinimum(1)
        self.edit_satir.setMaximum(50)
        self.edit_satir.setFixedWidth(100)
        self.edit_satir.valueChanged.connect(self.mark_form_modified)
        self.edit_satir.valueChanged.connect(self.update_edit_hint)
        satir_layout.addWidget(self.edit_satir)
        satir_layout.addWidget(QLabel("satır"))
        satir_layout.addStretch()
        form_layout.addRow("Boyuna Sıra *:", satir_layout)
        
        sutun_layout = QHBoxLayout()
        self.edit_sutun = QSpinBox()
        self.edit_sutun.setMinimum(1)
        self.edit_sutun.setMaximum(50)
        self.edit_sutun.setFixedWidth(100)
        self.edit_sutun.valueChanged.connect(self.mark_form_modified)
        self.edit_sutun.valueChanged.connect(self.update_edit_hint)
        sutun_layout.addWidget(self.edit_sutun)
        sutun_layout.addWidget(QLabel("sütun"))
        sutun_layout.addStretch()
        form_layout.addRow("Enine Sıra *:", sutun_layout)
        
        sira_layout = QHBoxLayout()
        self.edit_sira = QSpinBox()
        self.edit_sira.setMinimum(1)
        self.edit_sira.setMaximum(10)
        self.edit_sira.setFixedWidth(100)
        self.edit_sira.valueChanged.connect(self.mark_form_modified)
        sira_layout.addWidget(self.edit_sira)
        sira_layout.addWidget(QLabel("kişilik"))
        sira_layout.addStretch()
        form_layout.addRow("Sıra Yapısı *:", sira_layout)
        
        self.edit_hint = QLabel()
        self.edit_hint.setStyleSheet("color: #6b7280; font-size: 11px; padding: 4px;")
        form_layout.addRow("", self.edit_hint)
        
        edit_layout.addLayout(form_layout)
        
        # Edit buttons
        edit_btn_layout = QHBoxLayout()
        
        cancel_edit_btn = QPushButton("❌ İptal")
        cancel_edit_btn.setFixedHeight(40)
        cancel_edit_btn.clicked.connect(self.cancel_edit)
        
        self.save_edit_btn = QPushButton("💾 Değişiklikleri Kaydet")
        self.save_edit_btn.setObjectName("primaryBtn")
        self.save_edit_btn.setFixedHeight(40)
        self.save_edit_btn.setEnabled(False)
        self.save_edit_btn.clicked.connect(self.save_edit)
        
        edit_btn_layout.addWidget(cancel_edit_btn)
        edit_btn_layout.addWidget(self.save_edit_btn)
        edit_layout.addLayout(edit_btn_layout)
        
        layout.addWidget(self.edit_section)
        
        return tab
    
    def create_add_tab(self):
        """Create add new classroom tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Info
        info = QLabel("Yeni derslik eklemek için aşağıdaki formu doldurun:")
        info.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(info)
        
        # Form
        form_card = QGroupBox("Derslik Bilgileri")
        form_layout = QFormLayout(form_card)
        form_layout.setSpacing(16)
        form_layout.setContentsMargins(20, 20, 20, 20)
        
        self.add_kod = QLineEdit()
        self.add_kod.setPlaceholderText("örn: 301")
        self.add_kod.setFixedHeight(40)
        form_layout.addRow("Derslik Kodu *:", self.add_kod)
        
        self.add_ad = QLineEdit()
        self.add_ad.setPlaceholderText("örn: Amfi A")
        self.add_ad.setFixedHeight(40)
        form_layout.addRow("Derslik Adı *:", self.add_ad)
        
        kapasite_layout = QHBoxLayout()
        self.add_kapasite = QSpinBox()
        self.add_kapasite.setMinimum(1)
        self.add_kapasite.setMaximum(500)
        self.add_kapasite.setValue(42)
        self.add_kapasite.setFixedHeight(40)
        self.add_kapasite.setFixedWidth(120)
        kapasite_layout.addWidget(self.add_kapasite)
        kapasite_layout.addStretch()
        form_layout.addRow("Kapasite (Sınav) *:", kapasite_layout)
        
        satir_layout = QHBoxLayout()
        self.add_satir = QSpinBox()
        self.add_satir.setMinimum(1)
        self.add_satir.setMaximum(50)
        self.add_satir.setValue(7)
        self.add_satir.setFixedHeight(40)
        self.add_satir.setFixedWidth(120)
        self.add_satir.valueChanged.connect(self.update_add_hint)
        satir_layout.addWidget(self.add_satir)
        satir_layout.addWidget(QLabel("satır"))
        satir_layout.addStretch()
        form_layout.addRow("Boyuna Sıra Sayısı *:", satir_layout)
        
        sutun_layout = QHBoxLayout()
        self.add_sutun = QSpinBox()
        self.add_sutun.setMinimum(1)
        self.add_sutun.setMaximum(50)
        self.add_sutun.setValue(3)
        self.add_sutun.setFixedHeight(40)
        self.add_sutun.setFixedWidth(120)
        self.add_sutun.valueChanged.connect(self.update_add_hint)
        sutun_layout.addWidget(self.add_sutun)
        sutun_layout.addWidget(QLabel("sütun"))
        sutun_layout.addStretch()
        form_layout.addRow("Enine Sıra Sayısı *:", sutun_layout)
        
        sira_layout = QHBoxLayout()
        self.add_sira = QSpinBox()
        self.add_sira.setMinimum(1)
        self.add_sira.setMaximum(10)
        self.add_sira.setValue(2)
        self.add_sira.setFixedHeight(40)
        self.add_sira.setFixedWidth(120)
        sira_layout.addWidget(self.add_sira)
        sira_layout.addWidget(QLabel("kişilik"))
        sira_layout.addStretch()
        form_layout.addRow("Sıra Yapısı *:", sira_layout)
        
        self.add_hint = QLabel()
        self.add_hint.setStyleSheet("""
            color: #6b7280; 
            font-size: 12px; 
            padding: 8px 12px;
            background-color: #f3f4f6;
            border-radius: 4px;
        """)
        self.add_hint.setWordWrap(True)
        form_layout.addRow("", self.add_hint)
        self.update_add_hint()
        
        layout.addWidget(form_card)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("🔄 Formu Temizle")
        clear_btn.setFixedHeight(44)
        clear_btn.clicked.connect(self.clear_add_form)
        
        add_btn = QPushButton("💾 Dersliği Kaydet")
        add_btn.setObjectName("primaryBtn")
        add_btn.setFixedHeight(44)
        add_btn.clicked.connect(self.add_derslik)
        
        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(add_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        return tab
    
    def update_add_hint(self):
        """Update add form hint"""
        total = self.add_satir.value() * self.add_sutun.value()
        self.add_hint.setText(
            f"💡 Maksimum kapasite: {total} kişi "
            f"({self.add_satir.value()} satır × {self.add_sutun.value()} sütun)"
        )
    
    def update_edit_hint(self):
        """Update edit form hint"""
        total = self.edit_satir.value() * self.edit_sutun.value()
        self.edit_hint.setText(
            f"💡 Maksimum kapasite: {total} kişi "
            f"({self.edit_satir.value()} satır × {self.edit_sutun.value()} sütun)"
        )
    
    def mark_form_modified(self):
        """Mark form as modified"""
        self.form_modified = True
        self.save_edit_btn.setEnabled(True)
    
    def load_derslikler(self):
        """Load classrooms"""
        try:
            derslikler = self.derslik_model.get_derslikler_by_bolum(self.bolum_id)
            self.populate_table(derslikler)
            self.update_stats(len(derslikler))
        except Exception as e:
            logger.error(f"Error loading classrooms: {e}")
            QMessageBox.critical(self, "Hata", f"Derslikler yüklenirken hata oluştu:\n{str(e)}")
    
    def populate_table(self, derslikler):
        """Populate table"""
        self.table.setRowCount(0)
        
        for row, derslik in enumerate(derslikler):
            self.table.insertRow(row)
            
            # Store derslik_id in hidden data
            for col in range(7):
                item = QTableWidgetItem()
                if col == 0:
                    item.setText(str(derslik['derslik_kodu']))
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                elif col == 1:
                    item.setText(str(derslik['derslik_adi']))
                elif col == 2:
                    item.setText(str(derslik['kapasite']))
                    item.setTextAlignment(Qt.AlignCenter)
                elif col == 3:
                    item.setText(str(derslik['satir_sayisi']))
                    item.setTextAlignment(Qt.AlignCenter)
                elif col == 4:
                    item.setText(str(derslik['sutun_sayisi']))
                    item.setTextAlignment(Qt.AlignCenter)
                elif col == 5:
                    item.setText(f"{derslik['sira_yapisi']}'li")
                    item.setTextAlignment(Qt.AlignCenter)
                
                # Store full derslik data
                item.setData(Qt.UserRole, derslik)
                
                if col < 6:
                    self.table.setItem(row, col, item)
            
            # Action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(8, 4, 8, 4)
            action_layout.setSpacing(10)
            
            view_btn = QPushButton("🖼️ Görsel")
            view_btn.setFixedHeight(36)
            view_btn.setMinimumWidth(90)
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setStyleSheet("background-color: #3b82f6; color: white;")
            view_btn.clicked.connect(lambda checked=False, d=dict(derslik): self.visualize_derslik(d))
            
            edit_btn = QPushButton("✏️ Düzenle")
            edit_btn.setFixedHeight(36)
            edit_btn.setMinimumWidth(90)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setProperty('derslik_id', derslik['derslik_id'])
            edit_btn.clicked.connect(lambda checked=False, d=dict(derslik): self.edit_derslik(d))
            
            delete_btn = QPushButton("🗑️ Sil")
            delete_btn.setObjectName("dangerBtn")
            delete_btn.setFixedHeight(36)
            delete_btn.setMinimumWidth(80)
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setProperty('derslik_id', derslik['derslik_id'])
            delete_btn.clicked.connect(lambda checked=False, d=dict(derslik): self.delete_derslik(d))
            
            action_layout.addWidget(view_btn)
            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)
            
            # Ensure actions column has enough intrinsic width
            action_widget.setMinimumWidth(290)
            self.table.setCellWidget(row, 6, action_widget)
    
    def filter_table(self):
        """Filter table"""
        search_text = self.search_input.text().lower()
        
        for row in range(self.table.rowCount()):
            kod = self.table.item(row, 0).text().lower()
            ad = self.table.item(row, 1).text().lower()
            
            if search_text in kod or search_text in ad:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)
    
    def visualize_derslik(self, derslik):
        """Visualize classroom layout"""
        dialog = DerslikVisualizationDialog(derslik, self)
        dialog.exec()
    
    def update_stats(self, count):
        """Update statistics"""
        self.stats_label.setText(f"📊 Toplam {count} derslik kayıtlı")
    
    def clear_add_form(self):
        """Clear add form"""
        self.add_kod.clear()
        self.add_ad.clear()
        self.add_kapasite.setValue(42)
        self.add_satir.setValue(7)
        self.add_sutun.setValue(3)
        self.add_sira.setValue(2)
        self.add_kod.setFocus()
    
    def add_derslik(self):
        """Add new classroom"""
        # Validate
        if not self.add_kod.text().strip():
            QMessageBox.warning(self, "Uyarı", "Derslik kodu boş olamaz!")
            self.add_kod.setFocus()
            return
        
        if not self.add_ad.text().strip():
            QMessageBox.warning(self, "Uyarı", "Derslik adı boş olamaz!")
            self.add_ad.setFocus()
            return
        
        max_kap = self.add_satir.value() * self.add_sutun.value()
        if self.add_kapasite.value() > max_kap:
            QMessageBox.warning(
                self, "Uyarı",
                f"Kapasite, satır×sütun ({max_kap}) değerinden büyük olamaz!"
            )
            return
        
        derslik_data = {
            'bolum_id': self.bolum_id,
            'derslik_kodu': self.add_kod.text().strip(),
            'derslik_adi': self.add_ad.text().strip(),
            'kapasite': self.add_kapasite.value(),
            'satir_sayisi': self.add_satir.value(),
            'sutun_sayisi': self.add_sutun.value(),
            'sira_yapisi': self.add_sira.value()
        }
        
        try:
            result = self.derslik_controller.create_derslik(derslik_data)
            if result['success']:
                QMessageBox.information(self, "Başarılı ✅", result['message'])
                self.load_derslikler()
                self.clear_add_form()
                # Switch to list tab
                self.tabs.setCurrentIndex(0)
            else:
                QMessageBox.warning(self, "Hata", result['message'])
        except Exception as e:
            logger.error(f"Error adding derslik: {e}")
            QMessageBox.critical(self, "Hata", f"Derslik eklenirken hata oluştu:\n{str(e)}")
    
    def edit_derslik(self, derslik):
        """Load derslik for editing"""
        self.selected_derslik = derslik
        self.form_modified = False
        
        # Load data
        self.edit_kod.setText(str(derslik['derslik_kodu']))
        self.edit_ad.setText(str(derslik['derslik_adi']))
        self.edit_kapasite.setValue(int(derslik['kapasite']))
        self.edit_satir.setValue(int(derslik['satir_sayisi']))
        self.edit_sutun.setValue(int(derslik['sutun_sayisi']))
        self.edit_sira.setValue(int(derslik['sira_yapisi']))
        
        # Show edit section
        self.edit_section.setVisible(True)
        self.edit_section.setTitle(f"✏️ '{derslik['derslik_adi']}' Düzenleniyor")
        self.save_edit_btn.setEnabled(False)
        self.form_modified = False
        
        # Scroll to edit section
        self.edit_kod.setFocus()
    
    def cancel_edit(self):
        """Cancel editing"""
        if self.form_modified:
            reply = QMessageBox.question(
                self, "Değişiklikleri İptal Et",
                "Kaydedilmemiş değişiklikler var. İptal etmek istediğinizden emin misiniz?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        self.edit_section.setVisible(False)
        self.selected_derslik = None
        self.form_modified = False
    
    def save_edit(self):
        """Save edited classroom"""
        if not self.selected_derslik:
            return
        
        # Validate
        if not self.edit_kod.text().strip():
            QMessageBox.warning(self, "Uyarı", "Derslik kodu boş olamaz!")
            self.edit_kod.setFocus()
            return
        
        if not self.edit_ad.text().strip():
            QMessageBox.warning(self, "Uyarı", "Derslik adı boş olamaz!")
            self.edit_ad.setFocus()
            return
        
        max_kap = self.edit_satir.value() * self.edit_sutun.value()
        if self.edit_kapasite.value() > max_kap:
            QMessageBox.warning(
                self, "Uyarı",
                f"Kapasite, satır×sütun ({max_kap}) değerinden büyük olamaz!"
            )
            return
        
        derslik_data = {
            'bolum_id': self.bolum_id,
            'derslik_kodu': self.edit_kod.text().strip(),
            'derslik_adi': self.edit_ad.text().strip(),
            'kapasite': self.edit_kapasite.value(),
            'satir_sayisi': self.edit_satir.value(),
            'sutun_sayisi': self.edit_sutun.value(),
            'sira_yapisi': self.edit_sira.value()
        }
        
        try:
            result = self.derslik_controller.update_derslik(
                self.selected_derslik['derslik_id'], 
                derslik_data
            )
            
            if result['success']:
                QMessageBox.information(self, "Başarılı ✅", result['message'])
                self.load_derslikler()
                self.edit_section.setVisible(False)
                self.selected_derslik = None
                self.form_modified = False
            else:
                QMessageBox.warning(self, "Hata", result['message'])
        except Exception as e:
            logger.error(f"Error updating derslik: {e}")
            QMessageBox.critical(self, "Hata", f"Derslik güncellenirken hata oluştu:\n{str(e)}")
    
    def delete_derslik(self, derslik):
        """Delete classroom"""
        reply = QMessageBox.question(
            self, "Derslik Sil",
            f"'{derslik['derslik_adi']}' dersliğini silmek istediğinizden emin misiniz?\n\n"
            f"📊 Kod: {derslik['derslik_kodu']}\n"
            f"👥 Kapasite: {derslik['kapasite']}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                result = self.derslik_controller.delete_derslik(derslik['derslik_id'])
                if result['success']:
                    QMessageBox.information(self, "Başarılı ✅", result['message'])
                    self.load_derslikler()
                    
                    # Hide edit section if this derslik was being edited
                    if self.selected_derslik and self.selected_derslik['derslik_id'] == derslik['derslik_id']:
                        self.edit_section.setVisible(False)
                        self.selected_derslik = None
                else:
                    QMessageBox.warning(self, "Hata", result['message'])
            except Exception as e:
                logger.error(f"Error deleting derslik: {e}")
                QMessageBox.critical(self, "Hata", f"Derslik silinirken hata oluştu:\n{str(e)}")


class DerslikVisualizationDialog(QDialog):
    """Dialog to visualize classroom seating layout"""
    
    def __init__(self, derslik, parent=None):
        super().__init__(parent)
        self.derslik = derslik
        self.setWindowTitle(f"Derslik Düzeni - {derslik['derslik_adi']}")
        self.setMinimumSize(900, 700)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup visualization UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QLabel(f"🏛 {self.derslik['derslik_adi']} ({self.derslik['derslik_kodu']})")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1e40af;")
        layout.addWidget(header)
        
        # Info cards
        info_layout = QHBoxLayout()
        info_layout.setSpacing(12)
        
        info_items = [
            ("📏 Düzen", f"{self.derslik['satir_sayisi']} Sıra × {self.derslik['sutun_sayisi']} Sütun"),
            ("👥 Kapasite", f"{self.derslik['kapasite']} kişi"),
            ("💺 Sıra Yapısı", f"{self.derslik['sira_yapisi']}'li")
        ]
        
        for title, value in info_items:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #eff6ff, stop:1 #dbeafe);
                    border: 2px solid #3b82f6;
                    border-radius: 12px;
                    padding: 12px;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(4)
            
            title_label = QLabel(title)
            title_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #1e40af;")
            
            value_label = QLabel(value)
            value_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e3a8a;")
            
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            
            info_layout.addWidget(card)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Legend
        legend_frame = QFrame()
        legend_frame.setStyleSheet("""
            QFrame {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.addWidget(QLabel("<b>Gösterge:</b>"))
        
        seat_label = QLabel("💺 Koltuk (Kullanılabilir)")
        seat_label.setStyleSheet("color: #10b981; font-weight: bold;")
        legend_layout.addWidget(seat_label)
        
        aisle_label = QLabel("🚶 Koridor")
        aisle_label.setStyleSheet("color: #9ca3af; font-weight: bold;")
        legend_layout.addWidget(aisle_label)
        
        legend_layout.addStretch()
        layout.addWidget(legend_frame)
        
        # Visualization
        visual_container = self.create_classroom_visualization()
        
        scroll = QScrollArea()
        scroll.setWidget(visual_container)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(scroll, 1)
        
        # Close button
        close_btn = QPushButton("Kapat")
        close_btn.setObjectName("primaryBtn")
        close_btn.setFixedHeight(40)
        close_btn.setFixedWidth(120)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)
    
    def create_classroom_visualization(self) -> QWidget:
        """Create visual representation of classroom"""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #e5e7eb;
                border-radius: 12px;
                padding: 24px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        
        # Grid layout
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(16, 16, 16, 16)
        
        rows = self.derslik['satir_sayisi']
        cols = self.derslik['sutun_sayisi']
        sira_yapisi = self.derslik['sira_yapisi']
        
        # Add board/front indicator
        board = QLabel("📋 TAHTA / ÖN")
        board.setAlignment(Qt.AlignCenter)
        board.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #3b82f6, stop:1 #2563eb);
            color: white;
            font-weight: bold;
            font-size: 16px;
            padding: 16px;
            border-radius: 10px;
        """)
        grid.addWidget(board, 0, 0, 1, max(cols, 1))
        
        # Create seats
        seat_num = 1
        for row in range(1, rows + 1):
            col_idx = 0
            
            # Determine grouping pattern
            if sira_yapisi == 2:
                # 2-corridor-2-corridor-2 pattern
                groups_per_row = (cols + 1) // 3  # Approximate
            elif sira_yapisi == 3:
                # 3-corridor-3 pattern
                groups_per_row = (cols + 1) // 4  # Approximate
            else:
                # Single seats
                groups_per_row = cols
            
            remaining_cols = cols
            while remaining_cols > 0 and col_idx < cols * 2:  # *2 for aisles
                # Add a group of seats
                group_size = min(sira_yapisi, remaining_cols)
                
                for _ in range(group_size):
                    seat = QFrame()
                    seat.setFixedSize(75, 65)
                    
                    seat_layout = QVBoxLayout(seat)
                    seat_layout.setContentsMargins(4, 4, 4, 4)
                    seat_layout.setSpacing(2)
                    
                    seat.setStyleSheet("""
                        QFrame {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #d1fae5, stop:1 #a7f3d0);
                            border: 2px solid #10b981;
                            border-radius: 10px;
                        }
                    """)
                    
                    # Seat number
                    seat_label = QLabel(f"💺 #{seat_num}")
                    seat_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #065f46;")
                    seat_label.setAlignment(Qt.AlignCenter)
                    
                    # Position
                    pos_label = QLabel(f"S{row}:Sü{(col_idx % cols) + 1}")
                    pos_label.setStyleSheet("font-size: 9px; color: #047857;")
                    pos_label.setAlignment(Qt.AlignCenter)
                    
                    seat_layout.addWidget(seat_label)
                    seat_layout.addWidget(pos_label)
                    
                    grid.addWidget(seat, row, col_idx)
                    col_idx += 1
                    seat_num += 1
                    remaining_cols -= 1
                
                # Add aisle if there are more seats
                if remaining_cols > 0 and sira_yapisi > 1:
                    aisle = QLabel("🚶")
                    aisle.setFixedSize(50, 65)
                    aisle.setAlignment(Qt.AlignCenter)
                    aisle.setStyleSheet("""
                        background: #f9fafb;
                        border: 1px dashed #d1d5db;
                        border-radius: 8px;
                        color: #9ca3af;
                        font-size: 20px;
                    """)
                    grid.addWidget(aisle, row, col_idx)
                    col_idx += 1
        
        layout.addLayout(grid)
        
        # Statistics
        stats = QLabel(
            f"📊 Toplam Koltuk: {self.derslik['kapasite']} | "
            f"Düzen: {rows} Sıra × {cols} Sütun | "
            f"Yapı: {sira_yapisi}'li sıralar"
        )
        stats.setStyleSheet("""
            color: #6b7280;
            font-size: 13px;
            font-weight: bold;
            padding: 16px;
            background: #f9fafb;
            border-radius: 8px;
        """)
        stats.setAlignment(Qt.AlignCenter)
        layout.addWidget(stats)
        
        return container
