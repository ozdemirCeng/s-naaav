"""
Oturma Planı (Seating Plan) View
Professional interface for generating student seating plans
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QMessageBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from models.database import db
from models.oturma_model import OturmaModel
from models.sinav_model import SinavModel
from controllers.oturma_controller import OturmaController
from algorithms.oturma_planlama import OturmaPlanlama

logger = logging.getLogger(__name__)


class OturmaPlanlamaThread(QThread):
    """Thread for seating plan generation"""
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, sinav_id):
        super().__init__()
        self.sinav_id = sinav_id
    
    def run(self):
        try:
            planlama = OturmaPlanlama()
            result = planlama.generate_seating_plan(self.sinav_id, progress_callback=self.progress.emit)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class OturmaPaniView(QWidget):
    """Seating plan view"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id', 1)
        
        self.oturma_model = OturmaModel(db)
        self.sinav_model = SinavModel(db)
        self.oturma_controller = OturmaController(self.oturma_model, self.sinav_model)
        
        self.setup_ui()
        self.load_sinavlar()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Oturma Planı Oluştur 📝")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addWidget(header)
        
        # Selection
        select_card = QGroupBox("Sınav Seçimi")
        select_layout = QVBoxLayout(select_card)
        select_layout.setSpacing(16)
        
        info_label = QLabel("Oturma planı oluşturmak istediğiniz sınavı seçin:")
        info_label.setStyleSheet("color: #6b7280; font-size: 13px;")
        select_layout.addWidget(info_label)
        
        combo_layout = QHBoxLayout()
        
        combo_label = QLabel("Sınav:")
        combo_label.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        
        self.sinav_combo = QComboBox()
        self.sinav_combo.setFixedHeight(40)
        self.sinav_combo.currentIndexChanged.connect(self.on_sinav_changed)
        
        combo_layout.addWidget(combo_label)
        combo_layout.addWidget(self.sinav_combo, 1)
        
        select_layout.addLayout(combo_layout)
        
        # Exam info
        self.exam_info_label = QLabel()
        self.exam_info_label.setStyleSheet("""
            background: #f3f4f6;
            border-radius: 8px;
            padding: 12px;
            color: #374151;
            font-size: 12px;
        """)
        self.exam_info_label.setVisible(False)
        select_layout.addWidget(self.exam_info_label)
        
        layout.addWidget(select_card)
        
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
        
        self.generate_btn = QPushButton("🎲 Oturma Planı Oluştur")
        self.generate_btn.setObjectName("primaryBtn")
        self.generate_btn.setFixedHeight(44)
        self.generate_btn.setFixedWidth(220)
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self.generate_plan)
        
        button_layout.addStretch()
        button_layout.addWidget(self.generate_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Results
        self.results_group = QGroupBox("Oturma Planı")
        self.results_group.setVisible(False)
        results_layout = QVBoxLayout(self.results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Öğrenci No", "Ad Soyad", "Derslik", "Satır", "Sütun"
        ])
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setAlternatingRowColors(True)
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        
        self.results_table.setColumnWidth(0, 120)
        self.results_table.setColumnWidth(2, 100)
        self.results_table.setColumnWidth(3, 80)
        self.results_table.setColumnWidth(4, 80)
        
        results_layout.addWidget(self.results_table)
        
        save_btn = QPushButton("💾 Oturma Planını Kaydet")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.save_plan)
        
        results_layout.addWidget(save_btn)
        
        layout.addWidget(self.results_group)
        layout.addStretch()
    
    def load_sinavlar(self):
        """Load exams"""
        try:
            # Get all programs for the department
            programlar = self.sinav_model.get_programs_by_bolum(self.bolum_id)
            
            self.sinav_combo.clear()
            self.sinavlar = []
            
            for program in programlar:
                sinavlar = self.sinav_model.get_sinavlar_by_program(program['program_id'])
                
                for sinav in sinavlar:
                    display_text = f"{sinav['ders_kodu']} - {sinav['ders_adi']} ({sinav['tarih_saat']})"
                    self.sinav_combo.addItem(display_text)
                    self.sinavlar.append(sinav)
            
            if not self.sinavlar:
                QMessageBox.information(
                    self,
                    "Bilgi",
                    "Henüz sınav programı oluşturulmamış.\nÖnce 'Sınav Programı' sayfasından program oluşturun."
                )
                
        except Exception as e:
            logger.error(f"Error loading exams: {e}")
            QMessageBox.critical(self, "Hata", f"Sınavlar yüklenirken hata oluştu:\n{str(e)}")
    
    def on_sinav_changed(self, index):
        """Handle exam selection change"""
        if index >= 0 and index < len(self.sinavlar):
            sinav = self.sinavlar[index]
            
            self.exam_info_label.setText(
                f"📚 Ders: {sinav['ders_kodu']} - {sinav['ders_adi']}\n"
                f"📅 Tarih: {sinav['tarih_saat']}\n"
                f"👥 Öğrenci Sayısı: {sinav.get('ogrenci_sayisi', 'Bilinmiyor')}\n"
                f"🏛 Derslik: {sinav.get('derslik_kodu', 'Bilinmiyor')}"
            )
            self.exam_info_label.setVisible(True)
            self.generate_btn.setEnabled(True)
        else:
            self.exam_info_label.setVisible(False)
            self.generate_btn.setEnabled(False)
    
    def generate_plan(self):
        """Generate seating plan"""
        if not self.sinavlar or self.sinav_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir sınav seçin!")
            return
        
        sinav = self.sinavlar[self.sinav_combo.currentIndex()]
        sinav_id = sinav['sinav_id']
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Oturma planı oluşturuluyor...")
        self.generate_btn.setEnabled(False)
        
        # Start planning thread
        self.planning_thread = OturmaPlanlamaThread(sinav_id)
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
        self.generate_btn.setEnabled(True)
        
        if result.get('success'):
            self.current_plan = result['plan']
            self.display_plan(result['plan'])
            QMessageBox.information(
                self,
                "Başarılı",
                f"✅ Oturma planı başarıyla oluşturuldu!\n\n"
                f"Toplam {len(result['plan'])} öğrenci yerleştirildi."
            )
        else:
            QMessageBox.warning(self, "Uyarı", result.get('message', 'Plan oluşturulamadı!'))
    
    def on_planning_error(self, error_msg):
        """Handle planning error"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.generate_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Hata", f"Plan oluşturulurken hata oluştu:\n{error_msg}")
    
    def display_plan(self, plan):
        """Display generated seating plan"""
        self.results_group.setVisible(True)
        self.results_table.setRowCount(0)
        
        for row, oturma in enumerate(plan):
            self.results_table.insertRow(row)
            
            self.results_table.setItem(row, 0, QTableWidgetItem(str(oturma.get('ogrenci_no', ''))))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(oturma.get('ad_soyad', ''))))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(oturma.get('derslik_kodu', ''))))
            
            satir_item = QTableWidgetItem(str(oturma.get('satir', '')))
            satir_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(row, 3, satir_item)
            
            sutun_item = QTableWidgetItem(str(oturma.get('sutun', '')))
            sutun_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(row, 4, sutun_item)
    
    def save_plan(self):
        """Save seating plan to database"""
        if not hasattr(self, 'current_plan') or not self.current_plan:
            QMessageBox.warning(self, "Uyarı", "Kaydedilecek plan bulunamadı!")
            return
        
        reply = QMessageBox.question(
            self,
            "Planı Kaydet",
            f"{len(self.current_plan)} öğrencinin oturma planını kaydetmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            try:
                sinav = self.sinavlar[self.sinav_combo.currentIndex()]
                result = self.oturma_controller.save_seating_plan(sinav['sinav_id'], self.current_plan)
                
                if result['success']:
                    QMessageBox.information(self, "Başarılı", result['message'])
                    self.current_plan = []
                    self.results_group.setVisible(False)
                else:
                    QMessageBox.warning(self, "Hata", result['message'])
                    
            except Exception as e:
                logger.error(f"Error saving seating plan: {e}")
                QMessageBox.critical(self, "Hata", f"Plan kaydedilirken hata oluştu:\n{str(e)}")
