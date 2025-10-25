"""
Bolum Secim View - Department Selection
Admin kullanicilari icin bolum secim ekrani
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models.database import db
from models.bolum_model import BolumModel

logger = logging.getLogger(__name__)


class BolumCard(QFrame):
    """Department selection card"""
    
    clicked = Signal(dict)
    
    def __init__(self, bolum_data, parent=None):
        super().__init__(parent)
        self.bolum_data = bolum_data
        self.setCursor(Qt.PointingHandCursor)
        
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        # Icon
        icon = QLabel("🎓")
        icon.setFont(QFont("Segoe UI Emoji", 48))
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        
        # Department code
        kod = QLabel(self.bolum_data.get('bolum_kodu', ''))
        kod.setFont(QFont("Segoe UI", 14, QFont.Bold))
        kod.setAlignment(Qt.AlignCenter)
        kod.setStyleSheet("color: #10b981;")
        layout.addWidget(kod)
        
        # Department name
        ad = QLabel(self.bolum_data.get('bolum_adi', ''))
        ad.setFont(QFont("Segoe UI", 12))
        ad.setAlignment(Qt.AlignCenter)
        ad.setWordWrap(True)
        ad.setStyleSheet("color: #64748b;")
        layout.addWidget(ad)
        
        # Select button
        btn = QPushButton("Sec")
        btn.setObjectName("primaryBtn")
        btn.setFixedHeight(36)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.clicked.emit(self.bolum_data))
        layout.addWidget(btn)
    
    def apply_styles(self):
        """Apply styles"""
        self.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 16px;
            }
            QFrame:hover {
                border: 2px solid #10b981;
                background: #f0fdf4;
            }
            QPushButton#primaryBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #14b8a6);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 16px;
            }
            QPushButton#primaryBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #059669, stop:1 #0d9488);
            }
        """)


class BolumSecimView(QWidget):
    """Department selection view for Admin users"""
    
    bolum_selected = Signal(dict)
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_model = BolumModel(db)
        
        self.setup_ui()
        self.load_bolumler()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #10b981, stop:1 #14b8a6);
                border: none;
                border-radius: 0px;
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(48, 48, 48, 48)
        header_layout.setSpacing(12)
        
        title = QLabel("Bolum Secimi")
        title.setFont(QFont("Segoe UI", 32, QFont.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel(
            "Lutfen calismak istediginiz bolumu seciniz.\n"
            "Sectiginiz bolum icin ders, ogrenci ve sinav yonetimi yapabileceksiniz."
        )
        subtitle.setFont(QFont("Segoe UI", 13))
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.9); background: transparent;")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header)
        
        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(48, 48, 48, 48)
        
        # Scroll area for departments
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.bolum_container = QWidget()
        self.bolum_layout = QHBoxLayout(self.bolum_container)
        self.bolum_layout.setSpacing(24)
        self.bolum_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.bolum_container)
        content_layout.addWidget(scroll)
        
        layout.addWidget(content, 1)
    
    def load_bolumler(self):
        """Load departments"""
        try:
            bolumler = self.bolum_model.get_all_bolumler()
            
            if not bolumler:
                self.show_no_departments()
                return
            
            # Clear existing
            while self.bolum_layout.count():
                item = self.bolum_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Add department cards
            self.bolum_layout.addStretch()
            for bolum in bolumler:
                card = BolumCard(bolum)
                card.clicked.connect(self.on_bolum_selected)
                card.setFixedWidth(280)
                card.setFixedHeight(300)
                self.bolum_layout.addWidget(card)
            self.bolum_layout.addStretch()
            
            logger.info(f"Loaded {len(bolumler)} departments")
            
        except Exception as e:
            logger.error(f"Error loading departments: {e}")
            QMessageBox.critical(
                self,
                "Hata",
                f"Bolumler yuklenirken hata olustu:\n{str(e)}"
            )
    
    def show_no_departments(self):
        """Show message when no departments available"""
        self.bolum_layout.addStretch()
        
        msg = QLabel("Henuz tanimli bolum bulunmuyor")
        msg.setFont(QFont("Segoe UI", 16))
        msg.setStyleSheet("color: #6b7280;")
        msg.setAlignment(Qt.AlignCenter)
        
        self.bolum_layout.addWidget(msg)
        self.bolum_layout.addStretch()
    
    def on_bolum_selected(self, bolum_data):
        """Handle department selection"""
        logger.info(f"Department selected: {bolum_data['bolum_adi']}")
        
        # Show confirmation
        reply = QMessageBox.question(
            self,
            "Bolum Secimi",
            f"'{bolum_data['bolum_adi']}' bolumu icin islemlere devam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.bolum_selected.emit(bolum_data)

