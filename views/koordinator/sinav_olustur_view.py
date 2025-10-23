"""
Sınav Oluştur (Exam Create) View
Professional interface for creating exam schedules
"""

import logging
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QDateTimeEdit, QMessageBox,
    QGroupBox, QFormLayout, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar
)
from PySide6.QtCore import Qt, QDateTime, QThread, Signal
from PySide6.QtGui import QFont

from models.database import db
from models.sinav_model import SinavModel
from models.ders_model import DersModel
from models.derslik_model import DerslikModel
from controllers.sinav_controller import SinavController
from algorithms.sinav_planlama import SinavPlanlama

logger = logging.getLogger(__name__)


class SinavPlanlamaThread(QThread):
    """Thread for exam planning algorithm"""
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, params):
        super().__init__()
        self.params = params
    
    def run(self):
        try:
            planlama = SinavPlanlama()
            result = planlama.plan_exam_schedule(self.params, progress_callback=self.progress.emit)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SinavOlusturView(QWidget):
    """Exam schedule creation view"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id', 1)
        
        self.sinav_model = SinavModel(db)
        self.ders_model = DersModel(db)
        self.derslik_model = DerslikModel(db)
        self.sinav_controller = SinavController(self.sinav_model, self.ders_model, self.derslik_model)
        
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Sınav Programı Oluştur 📅")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addWidget(header)
        
        # Parameters
        params_card = QGroupBox("Sınav Parametreleri")
        params_layout = QFormLayout(params_card)
        params_layout.setSpacing(16)
        
        self.sinav_tipi_combo = QComboBox()
        self.sinav_tipi_combo.addItems(["Vize", "Final", "Bütünleme"])
        params_layout.addRow("Sınav Tipi:", self.sinav_tipi_combo)
        
        self.baslangic_tarih = QDateTimeEdit()
        self.baslangic_tarih.setDateTime(QDateTime.currentDateTime().addDays(7))
        self.baslangic_tarih.setCalendarPopup(True)
        self.baslangic_tarih.setDisplayFormat("dd.MM.yyyy HH:mm")
        params_layout.addRow("Başlangıç Tarihi:", self.baslangic_tarih)
        
        self.bitis_tarih = QDateTimeEdit()
        self.bitis_tarih.setDateTime(QDateTime.currentDateTime().addDays(14))
        self.bitis_tarih.setCalendarPopup(True)
        self.bitis_tarih.setDisplayFormat("dd.MM.yyyy HH:mm")
        params_layout.addRow("Bitiş Tarihi:", self.bitis_tarih)
        
        self.gun_basina_sinav = QSpinBox()
        self.gun_basina_sinav.setMinimum(1)
        self.gun_basina_sinav.setMaximum(10)
        self.gun_basina_sinav.setValue(3)
        params_layout.addRow("Gün Başına Sınav:", self.gun_basina_sinav)
        
        self.sinav_suresi = QSpinBox()
        self.sinav_suresi.setMinimum(60)
        self.sinav_suresi.setMaximum(240)
        self.sinav_suresi.setValue(120)
        self.sinav_suresi.setSuffix(" dakika")
        params_layout.addRow("Sınav Süresi:", self.sinav_suresi)
        
        self.ara_suresi = QSpinBox()
        self.ara_suresi.setMinimum(0)
        self.ara_suresi.setMaximum(120)
        self.ara_suresi.setValue(30)
        self.ara_suresi.setSuffix(" dakika")
        params_layout.addRow("Aralar Süresi:", self.ara_suresi)
        
        layout.addWidget(params_card)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self.progress_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("🚀 Programı Oluştur")
        self.create_btn.setObjectName("primaryBtn")
        self.create_btn.setFixedHeight(44)
        self.create_btn.setFixedWidth(200)
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.clicked.connect(self.create_schedule)
        
        button_layout.addStretch()
        button_layout.addWidget(self.create_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Results table
        self.results_group = QGroupBox("Oluşturulan Program")
        self.results_group.setVisible(False)
        results_layout = QVBoxLayout(self.results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Tarih/Saat", "Ders Kodu", "Ders Adı", "Derslik", "Öğrenci Sayısı"
        ])
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setAlternatingRowColors(True)
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        
        self.results_table.setColumnWidth(0, 150)
        self.results_table.setColumnWidth(1, 100)
        self.results_table.setColumnWidth(3, 100)
        self.results_table.setColumnWidth(4, 120)
        
        results_layout.addWidget(self.results_table)
        
        save_btn = QPushButton("💾 Programı Kaydet")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.save_schedule)
        
        results_layout.addWidget(save_btn)
        
        layout.addWidget(self.results_group)
        layout.addStretch()
    
    def load_data(self):
        """Load necessary data"""
        try:
            # Load courses and classrooms to verify availability
            dersler = self.ders_model.get_dersler_by_bolum(self.bolum_id)
            derslikler = self.derslik_model.get_derslikler_by_bolum(self.bolum_id)
            
            if not dersler:
                QMessageBox.warning(self, "Uyarı", "Henüz ders tanımlanmamış!")
            
            if not derslikler:
                QMessageBox.warning(self, "Uyarı", "Henüz derslik tanımlanmamış!")
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def create_schedule(self):
        """Create exam schedule"""
        # Validate dates
        if self.baslangic_tarih.dateTime() >= self.bitis_tarih.dateTime():
            QMessageBox.warning(self, "Uyarı", "Bitiş tarihi başlangıç tarihinden sonra olmalıdır!")
            return
        
        params = {
            'bolum_id': self.bolum_id,
            'sinav_tipi': self.sinav_tipi_combo.currentText(),
            'baslangic_tarih': self.baslangic_tarih.dateTime().toPython(),
            'bitis_tarih': self.bitis_tarih.dateTime().toPython(),
            'gun_basina_sinav': self.gun_basina_sinav.value(),
            'sinav_suresi': self.sinav_suresi.value(),
            'ara_suresi': self.ara_suresi.value()
        }
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Sınav programı oluşturuluyor...")
        self.create_btn.setEnabled(False)
        
        # Start planning thread
        self.planning_thread = SinavPlanlamaThread(params)
        self.planning_thread.progress.connect(self.on_planning_progress)
        self.planning_thread.finished.connect(self.on_planning_finished)
        self.planning_thread.error.connect(self.on_planning_error)
        self.planning_thread.start()
    
    def on_planning_progress(self, percent, message):
        """Update planning progress"""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)
    
    def on_planning_finished(self, result):
        """Handle planning completion"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.create_btn.setEnabled(True)
        
        if result.get('success'):
            self.current_schedule = result['schedule']
            self.display_schedule(result['schedule'])
            QMessageBox.information(
                self,
                "Başarılı",
                f"✅ Sınav programı başarıyla oluşturuldu!\n\n"
                f"Toplam {len(result['schedule'])} sınav planlandı."
            )
        else:
            QMessageBox.warning(self, "Uyarı", result.get('message', 'Program oluşturulamadı!'))
    
    def on_planning_error(self, error_msg):
        """Handle planning error"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.create_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Hata", f"Program oluşturulurken hata oluştu:\n{error_msg}")
    
    def display_schedule(self, schedule):
        """Display created schedule"""
        self.results_group.setVisible(True)
        self.results_table.setRowCount(0)
        
        for row, sinav in enumerate(schedule):
            self.results_table.insertRow(row)
            
            tarih = datetime.fromisoformat(sinav['tarih_saat']) if isinstance(sinav['tarih_saat'], str) else sinav['tarih_saat']
            tarih_str = tarih.strftime("%d.%m.%Y %H:%M")
            
            self.results_table.setItem(row, 0, QTableWidgetItem(tarih_str))
            self.results_table.setItem(row, 1, QTableWidgetItem(sinav.get('ders_kodu', '')))
            self.results_table.setItem(row, 2, QTableWidgetItem(sinav.get('ders_adi', '')))
            self.results_table.setItem(row, 3, QTableWidgetItem(sinav.get('derslik_kodu', '')))
            
            ogrenci_item = QTableWidgetItem(str(sinav.get('ogrenci_sayisi', 0)))
            ogrenci_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(row, 4, ogrenci_item)
    
    def save_schedule(self):
        """Save schedule to database"""
        if not hasattr(self, 'current_schedule') or not self.current_schedule:
            QMessageBox.warning(self, "Uyarı", "Kaydedilecek program bulunamadı!")
            return
        
        reply = QMessageBox.question(
            self,
            "Programı Kaydet",
            f"{len(self.current_schedule)} sınavı veritabanına kaydetmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            try:
                result = self.sinav_controller.save_exam_schedule(self.current_schedule)
                
                if result['success']:
                    QMessageBox.information(self, "Başarılı", result['message'])
                    self.current_schedule = []
                    self.results_group.setVisible(False)
                else:
                    QMessageBox.warning(self, "Hata", result['message'])
                    
            except Exception as e:
                logger.error(f"Error saving schedule: {e}")
                QMessageBox.critical(self, "Hata", f"Program kaydedilirken hata oluştu:\n{str(e)}")
