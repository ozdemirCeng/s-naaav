"""
Admin Sistem Ayarları View
Uygulama genel ayarları (JSON tabanlı)
"""

import json
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGroupBox, QFormLayout, QLineEdit, QSpinBox,
    QCheckBox, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


SETTINGS_PATH = Path(__file__).parent.parent.parent / 'config' / 'system_settings.json'


class SistemAyarlarView(QWidget):
    """Admin sistem ayarları (JSON depolama)"""

    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self._settings = {}
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("⚙️ Sistem Ayarları")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))

        subtitle = QLabel("Uygulama genel tercihleri ve bağlantı ayarları")
        subtitle.setStyleSheet("color: #666; font-size: 13px;")

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        layout.addWidget(header)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #e0e0e0; max-height: 1px;")
        layout.addWidget(divider)

        # General application settings
        app_group = QGroupBox("🖥️ Uygulama")
        app_form = QFormLayout(app_group)
        app_form.setSpacing(12)
        app_form.setContentsMargins(16, 16, 16, 16)

        self.default_theme = QComboBox()
        self.default_theme.addItems(["Açık", "Koyu", "Sistem"])  # 0,1,2
        self.log_level = QComboBox()
        self.log_level.addItems(["ERROR", "WARNING", "INFO", "DEBUG"])  # default INFO

        app_form.addRow("Tema (varsayılan):", self.default_theme)
        app_form.addRow("Log seviyesi:", self.log_level)

        layout.addWidget(app_group)

        # Database settings
        db_group = QGroupBox("🗄️ Veritabanı Bağlantısı")
        db_form = QFormLayout(db_group)
        db_form.setSpacing(12)
        db_form.setContentsMargins(16, 16, 16, 16)

        self.db_host = QLineEdit()
        self.db_port = QSpinBox()
        self.db_port.setRange(1, 65535)
        self.db_name = QLineEdit()
        self.db_user = QLineEdit()
        self.db_pass = QLineEdit()
        self.db_pass.setEchoMode(QLineEdit.Password)

        db_form.addRow("Host:", self.db_host)
        db_form.addRow("Port:", self.db_port)
        db_form.addRow("Veritabanı Adı:", self.db_name)
        db_form.addRow("Kullanıcı:", self.db_user)
        db_form.addRow("Şifre:", self.db_pass)

        test_btn = QPushButton("🔌 Bağlantıyı Test Et")
        test_btn.setFixedHeight(36)
        test_btn.clicked.connect(self._test_db_connection)
        db_form.addRow("", test_btn)

        layout.addWidget(db_group)

        # Email settings (optional)
        mail_group = QGroupBox("✉️ E-posta (opsiyonel)")
        mail_form = QFormLayout(mail_group)
        mail_form.setSpacing(12)
        mail_form.setContentsMargins(16, 16, 16, 16)

        self.smtp_host = QLineEdit()
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_user = QLineEdit()
        self.smtp_pass = QLineEdit()
        self.smtp_pass.setEchoMode(QLineEdit.Password)
        self.smtp_from = QLineEdit()

        mail_form.addRow("SMTP Host:", self.smtp_host)
        mail_form.addRow("SMTP Port:", self.smtp_port)
        mail_form.addRow("SMTP Kullanıcı:", self.smtp_user)
        mail_form.addRow("SMTP Şifre:", self.smtp_pass)
        mail_form.addRow("Gönderen Adresi:", self.smtp_from)

        layout.addWidget(mail_group)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        self.reset_btn = QPushButton("↺ Varsayılana Dön")
        self.reset_btn.setFixedHeight(40)
        self.reset_btn.clicked.connect(self._reset)
        self.save_btn = QPushButton("💾 Ayarları Kaydet")
        self.save_btn.setFixedHeight(40)
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.clicked.connect(self._save)
        btns.addWidget(self.reset_btn)
        btns.addWidget(self.save_btn)
        layout.addLayout(btns)
        layout.addStretch()

    def _defaults(self) -> dict:
        return {
            'app': {
                'theme': 0,
                'log_level': 2  # INFO
            },
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'sinav_takvimi_db',
                'user': 'postgres',
                'password': ''
            },
            'email': {
                'host': 'smtp.gmail.com',
                'port': 587,
                'user': '',
                'password': '',
                'from': 'noreply@kocaeli.edu.tr'
            }
        }

    def _apply_to_widgets(self, data: dict):
        app = data.get('app', {})
        self.default_theme.setCurrentIndex(int(app.get('theme', 0)))
        self.log_level.setCurrentIndex(int(app.get('log_level', 2)))

        dbset = data.get('database', {})
        self.db_host.setText(str(dbset.get('host', 'localhost')))
        self.db_port.setValue(int(dbset.get('port', 5432)))
        self.db_name.setText(str(dbset.get('name', 'sinav_takvimi_db')))
        self.db_user.setText(str(dbset.get('user', 'postgres')))
        self.db_pass.setText(str(dbset.get('password', '')))

        mail = data.get('email', {})
        self.smtp_host.setText(str(mail.get('host', '')))
        self.smtp_port.setValue(int(mail.get('port', 587)))
        self.smtp_user.setText(str(mail.get('user', '')))
        self.smtp_pass.setText(str(mail.get('password', '')))
        self.smtp_from.setText(str(mail.get('from', 'noreply@kocaeli.edu.tr')))

    def _collect_from_widgets(self) -> dict:
        return {
            'app': {
                'theme': self.default_theme.currentIndex(),
                'log_level': self.log_level.currentIndex()
            },
            'database': {
                'host': self.db_host.text().strip(),
                'port': self.db_port.value(),
                'name': self.db_name.text().strip(),
                'user': self.db_user.text().strip(),
                'password': self.db_pass.text().strip()
            },
            'email': {
                'host': self.smtp_host.text().strip(),
                'port': self.smtp_port.value(),
                'user': self.smtp_user.text().strip(),
                'password': self.smtp_pass.text().strip(),
                'from': self.smtp_from.text().strip()
            }
        }

    def _load(self):
        try:
            if SETTINGS_PATH.exists():
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
            else:
                self._settings = self._defaults()
            self._apply_to_widgets(self._settings)
            logger.info("System settings loaded")
        except Exception as e:
            logger.error(f"System settings load error: {e}")
            self._settings = self._defaults()
            self._apply_to_widgets(self._settings)

    def _save(self):
        try:
            data = self._collect_from_widgets()
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Başarılı", "✅ Sistem ayarları kaydedildi!\n\nNot: Veritabanı ayarları için uygulamayı yeniden başlatın.")
            logger.info("System settings saved")
        except Exception as e:
            logger.error(f"System settings save error: {e}")
            QMessageBox.critical(self, "Hata", f"Ayarlar kaydedilemedi:\n{str(e)}")

    def _reset(self):
        self._settings = self._defaults()
        self._apply_to_widgets(self._settings)
        QMessageBox.information(self, "Bilgi", "Ayarlar varsayılana alındı (kaydetmeyi unutmayın)")

    def _test_db_connection(self):
        try:
            import psycopg2
            params = {
                'host': self.db_host.text().strip() or 'localhost',
                'port': self.db_port.value() or 5432,
                'database': self.db_name.text().strip() or 'postgres',
                'user': self.db_user.text().strip() or 'postgres',
                'password': self.db_pass.text().strip(),
                'connect_timeout': 5
            }
            conn = psycopg2.connect(**params)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            conn.close()
            QMessageBox.information(self, "Başarılı", "✅ Veritabanı bağlantısı başarılı!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"❌ Bağlantı başarısız:\n{str(e)}")


