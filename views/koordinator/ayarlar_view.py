"""
Ayarlar (Settings) View
Professional interface for application settings and preferences
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QSpinBox, QCheckBox, QMessageBox,
    QGroupBox, QFormLayout, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from models.database import db

logger = logging.getLogger(__name__)


class AyarlarView(QWidget):
    """Settings view"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Ayarlar ⚙")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addWidget(header)
        
        # User info
        user_card = QGroupBox("Kullanıcı Bilgileri")
        user_layout = QFormLayout(user_card)
        user_layout.setSpacing(12)
        
        name_label = QLabel(self.user_data.get('ad_soyad', 'Kullanıcı'))
        name_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        user_layout.addRow("Ad Soyad:", name_label)
        
        email_label = QLabel(self.user_data.get('email', ''))
        user_layout.addRow("E-posta:", email_label)
        
        role_label = QLabel(self.user_data.get('role', ''))
        user_layout.addRow("Rol:", role_label)
        
        layout.addWidget(user_card)
        
        # Application settings
        app_card = QGroupBox("Uygulama Ayarları")
        app_layout = QFormLayout(app_card)
        app_layout.setSpacing(16)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Açık Tema", "Koyu Tema", "Sistem Teması"])
        app_layout.addRow("Tema:", self.theme_combo)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Türkçe", "English"])
        app_layout.addRow("Dil:", self.language_combo)
        
        self.auto_save_check = QCheckBox("Otomatik kaydetme")
        self.auto_save_check.setChecked(True)
        app_layout.addRow("", self.auto_save_check)
        
        self.notifications_check = QCheckBox("Bildirimler aktif")
        self.notifications_check.setChecked(True)
        app_layout.addRow("", self.notifications_check)
        
        layout.addWidget(app_card)
        
        # Exam settings
        exam_card = QGroupBox("Sınav Varsayılan Ayarları")
        exam_layout = QFormLayout(exam_card)
        exam_layout.setSpacing(16)
        
        self.default_duration = QSpinBox()
        self.default_duration.setMinimum(60)
        self.default_duration.setMaximum(240)
        self.default_duration.setValue(120)
        self.default_duration.setSuffix(" dakika")
        exam_layout.addRow("Varsayılan Sınav Süresi:", self.default_duration)
        
        self.default_break = QSpinBox()
        self.default_break.setMinimum(0)
        self.default_break.setMaximum(120)
        self.default_break.setValue(30)
        self.default_break.setSuffix(" dakika")
        exam_layout.addRow("Varsayılan Ara Süresi:", self.default_break)
        
        self.exams_per_day = QSpinBox()
        self.exams_per_day.setMinimum(1)
        self.exams_per_day.setMaximum(10)
        self.exams_per_day.setValue(3)
        exam_layout.addRow("Günlük Maksimum Sınav:", self.exams_per_day)
        
        layout.addWidget(exam_card)
        
        # Database settings
        db_card = QGroupBox("Veritabanı Ayarları")
        db_layout = QFormLayout(db_card)
        db_layout.setSpacing(12)
        
        self.db_host = QLineEdit()
        self.db_host.setPlaceholderText("localhost")
        db_layout.addRow("Host:", self.db_host)
        
        self.db_port = QSpinBox()
        self.db_port.setMinimum(1)
        self.db_port.setMaximum(65535)
        self.db_port.setValue(5432)
        db_layout.addRow("Port:", self.db_port)
        
        self.db_name = QLineEdit()
        self.db_name.setPlaceholderText("sinav_takvimi_db")
        db_layout.addRow("Veritabanı Adı:", self.db_name)
        
        test_db_btn = QPushButton("🔌 Bağlantıyı Test Et")
        test_db_btn.setFixedHeight(36)
        test_db_btn.clicked.connect(self.test_database_connection)
        db_layout.addRow("", test_db_btn)
        
        layout.addWidget(db_card)
        
        # Save button
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("↺ Varsayılana Dön")
        reset_btn.setFixedHeight(44)
        reset_btn.setFixedWidth(160)
        reset_btn.clicked.connect(self.reset_settings)
        
        save_btn = QPushButton("💾 Ayarları Kaydet")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(44)
        save_btn.setFixedWidth(160)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self.save_settings)
        
        button_layout.addStretch()
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
    
    def load_settings(self):
        """Load settings from database or config"""
        # Placeholder - implement based on your settings storage
        pass
    
    def save_settings(self):
        """Save settings"""
        try:
            # Placeholder - implement based on your settings storage
            
            QMessageBox.information(
                self,
                "Başarılı",
                "✅ Ayarlar başarıyla kaydedildi!"
            )
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Hata", f"Ayarlar kaydedilirken hata oluştu:\n{str(e)}")
    
    def reset_settings(self):
        """Reset settings to default"""
        reply = QMessageBox.question(
            self,
            "Ayarları Sıfırla",
            "Tüm ayarları varsayılan değerlere döndürmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset to defaults
            self.theme_combo.setCurrentIndex(0)
            self.language_combo.setCurrentIndex(0)
            self.auto_save_check.setChecked(True)
            self.notifications_check.setChecked(True)
            self.default_duration.setValue(120)
            self.default_break.setValue(30)
            self.exams_per_day.setValue(3)
            
            QMessageBox.information(self, "Başarılı", "Ayarlar varsayılan değerlere sıfırlandı!")
    
    def test_database_connection(self):
        """Test database connection"""
        try:
            if db.test_connection():
                QMessageBox.information(
                    self,
                    "Başarılı",
                    "✅ Veritabanı bağlantısı başarılı!"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Başarısız",
                    "❌ Veritabanı bağlantısı kurulamadı!"
                )
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            QMessageBox.critical(
                self,
                "Hata",
                f"Bağlantı testi sırasında hata oluştu:\n{str(e)}"
            )
