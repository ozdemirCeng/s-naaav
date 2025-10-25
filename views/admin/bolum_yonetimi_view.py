"""
Admin Bölüm Yönetimi View
Bölümleri ekle, düzenle, sil
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QHeaderView, QAbstractItemView,
    QToolButton, QStyle
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from models.bolum_model import BolumModel
from models.database import db

logger = logging.getLogger(__name__)


class BolumDialog(QDialog):
    """Dialog for adding/editing departments"""
    
    def __init__(self, bolum_data=None, parent=None):
        super().__init__(parent)
        self.bolum_data = bolum_data
        self.is_edit = bolum_data is not None
        
        self.setWindowTitle("Bölüm Düzenle" if self.is_edit else "Yeni Bölüm Ekle")
        self.setMinimumWidth(500)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Bölüm Kodu
        self.kod_input = QLineEdit()
        self.kod_input.setPlaceholderText("Örn: BLM")
        self.kod_input.setFixedHeight(36)
        self.kod_input.setMaxLength(20)
        if self.is_edit:
            self.kod_input.setText(self.bolum_data.get('bolum_kodu', ''))
        form_layout.addRow("Bölüm Kodu:", self.kod_input)
        
        # Bölüm Adı
        self.adi_input = QLineEdit()
        self.adi_input.setPlaceholderText("Örn: Bilgisayar Mühendisliği")
        self.adi_input.setFixedHeight(36)
        if self.is_edit:
            self.adi_input.setText(self.bolum_data.get('bolum_adi', ''))
        form_layout.addRow("Bölüm Adı:", self.adi_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        cancel_btn = QPushButton("İptal")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setFixedWidth(120)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("💾 Kaydet")
        save_btn.setFixedHeight(40)
        save_btn.setFixedWidth(120)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        save_btn.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def get_data(self):
        """Get form data"""
        return {
            'bolum_kodu': self.kod_input.text().strip().upper(),
            'bolum_adi': self.adi_input.text().strip()
        }


class BolumYonetimiView(QWidget):
    """Admin department management view"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_model = BolumModel(db)
        
        self.setup_ui()
        self.load_bolumler()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("🏢 Bölüm Yönetimi")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        
        subtitle = QLabel("Bölümleri ekleyin, düzenleyin veya silin")
        subtitle.setStyleSheet("color: #666; font-size: 13px;")
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        add_btn = QPushButton("➕ Yeni Bölüm Ekle")
        add_btn.setFixedHeight(44)
        add_btn.setFixedWidth(180)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.add_bolum)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(add_btn)
        
        layout.addWidget(header)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #e0e0e0; max-height: 1px;")
        layout.addWidget(divider)
        
        # Table Container
        table_container = QFrame()
        table_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Bölüm Kodu", "Bölüm Adı", "Koordinatör Sayısı", "İşlemler"
        ])
        
        # Behavior and scrolling
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.ElideRight)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        # Column widths and header alignment
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setMinimumSectionSize(60)
        header.setSectionsMovable(False)
        header.setSectionsClickable(False)
        header.setHighlightSections(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Bölüm Kodu
        header.setSectionResizeMode(1, QHeaderView.Fixed)           # Bölüm Adı (managed)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Koordinatör Sayısı
        header.setSectionResizeMode(3, QHeaderView.Fixed)             # İşlemler (managed)
        header.setFixedHeight(36)

        # Row height
        self.table.verticalHeader().setDefaultSectionSize(44)
        
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: none;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e8f5e9;
                color: #2c3e50;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px 6px;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        
        table_layout.addWidget(self.table)
        layout.addWidget(table_container)
        
        # Initial adjust
        self.adjust_columns()
    
    def load_bolumler(self):
        """Load all departments"""
        try:
            # Get all bolumler with coordinator count
            query = """
                SELECT b.bolum_id, b.bolum_kodu, b.bolum_adi,
                       COUNT(u.user_id) as koordinator_sayisi
                FROM bolumler b
                LEFT JOIN users u ON b.bolum_id = u.bolum_id 
                    AND u.role = 'Bölüm Koordinatörü' 
                    AND u.aktif = TRUE
                WHERE b.aktif = TRUE
                GROUP BY b.bolum_id, b.bolum_kodu, b.bolum_adi
                ORDER BY b.bolum_adi
            """
            bolumler = db.execute_query(query)
            
            self.table.setRowCount(0)
            
            for bolum in bolumler:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Bölüm Kodu
                kod_item = QTableWidgetItem(bolum['bolum_kodu'])
                kod_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                kod_item.setForeground(Qt.blue)
                self.table.setItem(row, 0, kod_item)
                
                # Bölüm Adı
                self.table.setItem(row, 1, QTableWidgetItem(bolum['bolum_adi']))
                
                # Koordinatör Sayısı
                koordinator_item = QTableWidgetItem(str(bolum['koordinator_sayisi']))
                koordinator_item.setTextAlignment(Qt.AlignCenter)
                if bolum['koordinator_sayisi'] == 0:
                    koordinator_item.setForeground(Qt.red)
                else:
                    koordinator_item.setForeground(Qt.darkGreen)
                self.table.setItem(row, 2, koordinator_item)
                
                # Actions
                action_widget = QWidget()
                action_widget.setMinimumWidth(220) # Ensure enough space for buttons
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(8, 4, 8, 4)
                action_layout.setSpacing(10)

                edit_btn = QPushButton("✏️ Düzenle")
                edit_btn.setFixedHeight(36)
                edit_btn.setMinimumWidth(90)
                edit_btn.setStyleSheet("background-color: #3498db; color: white; border: none; border-radius: 5px; font-weight: 600;")
                edit_btn.setCursor(Qt.PointingHandCursor)
                edit_btn.clicked.connect(lambda checked=False, b=bolum: self.edit_bolum(b))

                delete_btn = QPushButton("🗑️ Sil")
                delete_btn.setFixedHeight(36)
                delete_btn.setMinimumWidth(80)
                delete_btn.setStyleSheet("background-color: #e74c3c; color: white; border: none; border-radius: 5px; font-weight: 600;")
                delete_btn.setCursor(Qt.PointingHandCursor)
                delete_btn.clicked.connect(lambda checked=False, b=bolum: self.delete_bolum(b))
                
                # Disable delete if has coordinators
                if bolum['koordinator_sayisi'] > 0:
                    delete_btn.setEnabled(False)
                    delete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #95a5a6;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            font-size: 11px;
                        }
                    """)
                    delete_btn.setToolTip("Koordinatörü olan bölüm silinemez")
                
                action_layout.addWidget(edit_btn)
                action_layout.addWidget(delete_btn)
                action_layout.addStretch()
                
                self.table.setCellWidget(row, 3, action_widget)
            
            # Adjust after load
            self.adjust_columns()
            logger.info(f"Loaded {len(bolumler)} departments")
            
        except Exception as e:
            logger.error(f"Error loading departments: {e}")
            QMessageBox.critical(self, "Hata", f"Bölümler yüklenirken hata oluştu:\n{str(e)}")
    
    def add_bolum(self):
        """Add new department"""
        try:
            dialog = BolumDialog(parent=self)
            if dialog.exec() == QDialog.Accepted:
                data = dialog.get_data()
                
                # Validation
                if not data['bolum_kodu']:
                    QMessageBox.warning(self, "Uyarı", "⚠️ Bölüm kodu giriniz!")
                    return
                
                if not data['bolum_adi']:
                    QMessageBox.warning(self, "Uyarı", "⚠️ Bölüm adı giriniz!")
                    return
                
                # Check if kod already exists
                existing = self.bolum_model.get_bolum_by_kod(data['bolum_kodu'])
                if existing:
                    QMessageBox.warning(
                        self,
                        "Uyarı",
                        f"⚠️ '{data['bolum_kodu']}' kodu zaten kullanılıyor!\n\n"
                        f"Mevcut bölüm: {existing['bolum_adi']}"
                    )
                    return
                
                # Insert department
                bolum_id = self.bolum_model.insert_bolum(data)
                
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"✅ Bölüm başarıyla eklendi!\n\n"
                    f"Kod: {data['bolum_kodu']}\n"
                    f"Ad: {data['bolum_adi']}"
                )
                
                self.load_bolumler()
                
        except Exception as e:
            logger.error(f"Error adding department: {e}")
            QMessageBox.critical(self, "Hata", f"Bölüm eklenirken hata oluştu:\n{str(e)}")
    
    def edit_bolum(self, bolum):
        """Edit department"""
        try:
            dialog = BolumDialog(bolum_data=bolum, parent=self)
            if dialog.exec() == QDialog.Accepted:
                data = dialog.get_data()
                
                # Validation
                if not data['bolum_kodu']:
                    QMessageBox.warning(self, "Uyarı", "⚠️ Bölüm kodu giriniz!")
                    return
                
                if not data['bolum_adi']:
                    QMessageBox.warning(self, "Uyarı", "⚠️ Bölüm adı giriniz!")
                    return
                
                # Check if kod already exists (for other departments)
                existing = self.bolum_model.get_bolum_by_kod(data['bolum_kodu'])
                if existing and existing['bolum_id'] != bolum['bolum_id']:
                    QMessageBox.warning(
                        self,
                        "Uyarı",
                        f"⚠️ '{data['bolum_kodu']}' kodu zaten kullanılıyor!\n\n"
                        f"Mevcut bölüm: {existing['bolum_adi']}"
                    )
                    return
                
                # Update department
                self.bolum_model.update_bolum(bolum['bolum_id'], data)
                
                QMessageBox.information(
                    self,
                    "Başarılı",
                    "✅ Bölüm başarıyla güncellendi!"
                )
                
                self.load_bolumler()
                
        except Exception as e:
            logger.error(f"Error editing department: {e}")
            QMessageBox.critical(self, "Hata", f"Bölüm güncellenirken hata oluştu:\n{str(e)}")
    
    def delete_bolum(self, bolum):
        """Delete department"""
        try:
            reply = QMessageBox.question(
                self,
                "Bölüm Sil",
                f"🗑️ {bolum['bolum_adi']} bölümünü silmek istediğinizden emin misiniz?\n\n"
                f"Kod: {bolum['bolum_kodu']}\n\n"
                f"Bu işlem geri alınamaz!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.bolum_model.delete_bolum(bolum['bolum_id'])
                
                QMessageBox.information(
                    self,
                    "Başarılı",
                    "✅ Bölüm başarıyla silindi!"
                )
                
                self.load_bolumler()
                
        except Exception as e:
            logger.error(f"Error deleting department: {e}")
            QMessageBox.critical(self, "Hata", f"Bölüm silinirken hata oluştu:\n{str(e)}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            self.adjust_columns()
        except Exception:
            pass

    def adjust_columns(self):
        """Keep code/count to contents, actions to widget size, rest to name column."""
        if not hasattr(self, 'table'):
            return
        viewport_w = self.table.viewport().width()
        if viewport_w <= 0:
            return
        vbar = self.table.verticalScrollBar()
        scrollbar_w = vbar.width() if vbar and vbar.isVisible() else 0

        code_w = max(100, self.table.sizeHintForColumn(0))
        count_w = max(110, self.table.sizeHintForColumn(2))

        actions_w = 0
        for row in range(self.table.rowCount()):
            cw = self.table.cellWidget(row, 3)
            if cw:
                actions_w = max(actions_w, cw.sizeHint().width())
        if actions_w == 0:
            actions_w = 180
        actions_w = max(160, min(actions_w, 320))

        reserved = code_w + count_w + actions_w
        name_w = max(240, viewport_w - reserved - scrollbar_w)

        self.table.setColumnWidth(0, code_w)
        self.table.setColumnWidth(1, name_w)
        self.table.setColumnWidth(2, count_w)
        self.table.setColumnWidth(3, actions_w)

