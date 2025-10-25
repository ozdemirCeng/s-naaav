"""
Admin Duyuru Yönetimi View
Login ekranında gösterilecek duyuruları yönetme
"""

import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QCheckBox, QMessageBox, QDialog, QFormLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from models.database import db

logger = logging.getLogger(__name__)


class DuyuruDialog(QDialog):
    """Duyuru ekleme/düzenleme dialog"""
    
    def __init__(self, parent=None, duyuru_data=None):
        super().__init__(parent)
        self.duyuru_data = duyuru_data
        self.setWindowTitle("Duyuru Ekle" if not duyuru_data else "Duyuru Düzenle")
        self.setMinimumSize(600, 400)
        self._build_ui()
        
        if duyuru_data:
            self._load_data()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("📢 " + ("Yeni Duyuru" if not self.duyuru_data else "Duyuruyu Düzenle"))
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Form
        form = QFormLayout()
        form.setSpacing(12)
        
        # Duyuru metni
        self.metin_input = QTextEdit()
        self.metin_input.setPlaceholderText("Duyuru metnini buraya yazın...")
        self.metin_input.setMinimumHeight(200)
        self.metin_input.setFont(QFont("Segoe UI", 11))
        form.addRow("Duyuru Metni:", self.metin_input)
        
        # Aktif checkbox
        self.aktif_check = QCheckBox("Duyuru aktif (Login ekranında göster)")
        self.aktif_check.setChecked(True)
        self.aktif_check.setFont(QFont("Segoe UI", 10))
        form.addRow("", self.aktif_check)
        
        layout.addLayout(form)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("❌ İptal")
        cancel_btn.setFixedHeight(40)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("💾 Kaydet")
        save_btn.setFixedHeight(40)
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
    
    def _load_data(self):
        """Load existing announcement data"""
        if self.duyuru_data:
            self.metin_input.setPlainText(self.duyuru_data.get('metin', ''))
            self.aktif_check.setChecked(self.duyuru_data.get('aktif', True))
    
    def get_data(self):
        """Get form data"""
        return {
            'metin': self.metin_input.toPlainText().strip(),
            'aktif': self.aktif_check.isChecked()
        }


class DuyuruYonetimiView(QWidget):
    """Admin duyuru yönetimi - Login ekranı duyuruları"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self._build_ui()
        self._load_duyurular()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        
        title = QLabel("📢 Duyuru Yönetimi")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        
        subtitle = QLabel("Login ekranında gösterilecek duyuruları yönetin")
        subtitle.setStyleSheet("color: #666; font-size: 13px;")
        
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        # Add button
        add_btn = QPushButton("➕ Yeni Duyuru Ekle")
        add_btn.setFixedHeight(40)
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add_duyuru)
        header_layout.addWidget(add_btn)
        
        layout.addWidget(header)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #e0e0e0; max-height: 1px;")
        layout.addWidget(divider)
        
        # Info card
        info_card = QFrame()
        info_card.setObjectName("infoCard")
        info_card.setStyleSheet("""
            #infoCard {
                background: #E3F2FD;
                border-left: 4px solid #2196F3;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        info_layout = QHBoxLayout(info_card)
        info_icon = QLabel("ℹ️")
        info_icon.setFont(QFont("Segoe UI Emoji", 16))
        info_text = QLabel("Aktif duyurular login ekranının sol panelinde gösterilir. Birden fazla aktif duyuru olabilir.")
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #1565C0; font-size: 12px;")
        info_layout.addWidget(info_icon)
        info_layout.addWidget(info_text, 1)
        layout.addWidget(info_card)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Duyuru Metni', 'Durum', 'Oluşturulma', 'İşlemler'])
        
        # Table styling
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        
        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Metin
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Durum
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Tarih
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # İşlemler
        self.table.setColumnWidth(3, 200)
        
        layout.addWidget(self.table)
    
    def _load_duyurular(self):
        """Load announcements from database"""
        try:
            # Load announcements
            query = """
                SELECT 
                    d.duyuru_id,
                    d.metin,
                    d.aktif,
                    d.olusturulma_tarihi,
                    u.ad_soyad as olusturan
                FROM duyurular d
                LEFT JOIN users u ON d.olusturan_user_id = u.user_id
                ORDER BY d.olusturulma_tarihi DESC
            """
            results = db.execute_query(query)
            
            self.table.setRowCount(0)
            
            for row_idx, row in enumerate(results):
                self.table.insertRow(row_idx)
                
                # Metin (truncated)
                metin = row['metin']
                if len(metin) > 100:
                    metin = metin[:100] + "..."
                metin_item = QTableWidgetItem(metin)
                metin_item.setData(Qt.UserRole, row['duyuru_id'])
                self.table.setItem(row_idx, 0, metin_item)
                
                # Durum
                durum = "🟢 Aktif" if row['aktif'] else "🔴 Pasif"
                durum_item = QTableWidgetItem(durum)
                durum_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 1, durum_item)
                
                # Tarih
                tarih = row['olusturulma_tarihi'].strftime('%d.%m.%Y %H:%M') if row['olusturulma_tarihi'] else '-'
                tarih_item = QTableWidgetItem(tarih)
                tarih_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 2, tarih_item)
                
                # İşlemler
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 4, 4, 4)
                actions_layout.setSpacing(4)
                
                edit_btn = QPushButton("✏️ Düzenle")
                edit_btn.setFixedHeight(32)
                edit_btn.clicked.connect(lambda checked, r=row: self._edit_duyuru(r))
                
                delete_btn = QPushButton("🗑️ Sil")
                delete_btn.setFixedHeight(32)
                delete_btn.setProperty("class", "dangerBtn")
                delete_btn.clicked.connect(lambda checked, did=row['duyuru_id']: self._delete_duyuru(did))
                
                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(delete_btn)
                self.table.setCellWidget(row_idx, 3, actions_widget)
            
            logger.info(f"Loaded {len(results)} announcements")
            
        except Exception as e:
            logger.error(f"Error loading announcements: {e}")
            QMessageBox.critical(self, "Hata", f"Duyurular yüklenirken hata oluştu:\n{str(e)}")
    
    def _add_duyuru(self):
        """Add new announcement"""
        dialog = DuyuruDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            
            if not data['metin']:
                QMessageBox.warning(self, "Uyarı", "Duyuru metni boş olamaz!")
                return
            
            try:
                query = """
                    INSERT INTO duyurular (metin, aktif, olusturan_user_id)
                    VALUES (%s, %s, %s)
                """
                # Use context manager for INSERT (no results expected)
                with db.get_cursor(commit=True) as cursor:
                    cursor.execute(query, (data['metin'], data['aktif'], self.user_data['user_id']))
                
                QMessageBox.information(self, "Başarılı", "✅ Duyuru başarıyla eklendi!")
                self._load_duyurular()
                
            except Exception as e:
                logger.error(f"Error adding announcement: {e}")
                QMessageBox.critical(self, "Hata", f"Duyuru eklenirken hata oluştu:\n{str(e)}")
    
    def _edit_duyuru(self, row_data):
        """Edit announcement"""
        dialog = DuyuruDialog(self, row_data)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            
            if not data['metin']:
                QMessageBox.warning(self, "Uyarı", "Duyuru metni boş olamaz!")
                return
            
            try:
                query = """
                    UPDATE duyurular 
                    SET metin = %s, aktif = %s, guncelleme_tarihi = CURRENT_TIMESTAMP
                    WHERE duyuru_id = %s
                """
                # Use context manager for UPDATE (no results expected)
                with db.get_cursor(commit=True) as cursor:
                    cursor.execute(query, (data['metin'], data['aktif'], row_data['duyuru_id']))
                
                QMessageBox.information(self, "Başarılı", "✅ Duyuru başarıyla güncellendi!")
                self._load_duyurular()
                
            except Exception as e:
                logger.error(f"Error updating announcement: {e}")
                QMessageBox.critical(self, "Hata", f"Duyuru güncellenirken hata oluştu:\n{str(e)}")
    
    def _delete_duyuru(self, duyuru_id):
        """Delete announcement"""
        reply = QMessageBox.question(
            self,
            "Duyuru Sil",
            "Bu duyuruyu silmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                query = "DELETE FROM duyurular WHERE duyuru_id = %s"
                # Use context manager for DELETE (no results expected)
                with db.get_cursor(commit=True) as cursor:
                    cursor.execute(query, (duyuru_id,))
                
                QMessageBox.information(self, "Başarılı", "✅ Duyuru başarıyla silindi!")
                self._load_duyurular()
                
            except Exception as e:
                logger.error(f"Error deleting announcement: {e}")
                QMessageBox.critical(self, "Hata", f"Duyuru silinirken hata oluştu:\n{str(e)}")

