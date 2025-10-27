"""
Sınav Oluştur (Exam Create) View - REDESIGNED
Modern, user-friendly interface for creating exam schedules
"""

import logging
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QDateTimeEdit, QMessageBox,
    QGroupBox, QFormLayout, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar, QCheckBox,
    QLineEdit, QScrollArea, QFileDialog, QTabWidget, QDialog,
    QDialogButtonBox
)
from PySide6.QtCore import Qt, QDateTime, QThread, Signal
from PySide6.QtGui import QFont, QColor

from models.database import db
from models.sinav_model import SinavModel
from models.ders_model import DersModel
from models.derslik_model import DerslikModel
from models.ogrenci_model import OgrenciModel
from controllers.sinav_controller import SinavController
from algorithms.sinav_planlama import SinavPlanlama
from utils.export_utils import ExportUtils

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


class ProgramResultDialog(QDialog):
    """Dialog to show exam schedule results"""
    
    def __init__(self, schedule_data, params, parent=None):
        super().__init__(parent)
        self.schedule_data = schedule_data
        self.params = params
        self.bolum_id = params.get('bolum_id')
        self.setWindowTitle("📅 Sınav Programı Oluşturuldu")
        self.setMinimumSize(1000, 700)
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Success header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        header_layout = QVBoxLayout(header)
        
        title = QLabel("✅ Sınav Programı Başarıyla Oluşturuldu!")
        title.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        
        # Stats
        unique_exams = len(set((s.get('ders_id'), s.get('tarih_saat')) for s in self.schedule_data))
        unique_dates = len(set(
            (datetime.fromisoformat(s['tarih_saat']) if isinstance(s['tarih_saat'], str) else s['tarih_saat']).date()
            for s in self.schedule_data
        ))
        
        stats = QLabel(f"📊 {unique_exams} Sınav  •  📅 {unique_dates} Gün  •  🏛 {len(self.schedule_data)} Derslik Ataması")
        stats.setStyleSheet("color: white; font-size: 14px;")
        stats.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(stats)
        layout.addWidget(header)
        
        # Info message
        info_label = QLabel("Aşağıdaki tablodan programı inceleyebilir, Excel/PDF olarak indirebilir veya veritabanına kaydedebilirsiniz.")
        info_label.setStyleSheet("color: #6b7280; font-size: 13px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Tarih/Saat', 'Ders Kodu', 'Ders Adı', 'Öğretim Elemanı', 'Derslik', 'Öğrenci'])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        # Column widths - responsive
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        # Populate table
        for row_data in self.schedule_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            tarih = datetime.fromisoformat(row_data['tarih_saat']) if isinstance(row_data['tarih_saat'], str) else row_data['tarih_saat']
            tarih_str = tarih.strftime("%d.%m.%Y %H:%M")
            
            self.table.setItem(row, 0, QTableWidgetItem(tarih_str))
            self.table.setItem(row, 1, QTableWidgetItem(row_data.get('ders_kodu', '')))
            self.table.setItem(row, 2, QTableWidgetItem(row_data.get('ders_adi', '')))
            self.table.setItem(row, 3, QTableWidgetItem(row_data.get('ogretim_elemani', '')))
            self.table.setItem(row, 4, QTableWidgetItem(row_data.get('derslik_adi', row_data.get('derslik_kodu', ''))))
            
            ogrenci_item = QTableWidgetItem(str(row_data.get('ogrenci_sayisi', 0)))
            ogrenci_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, ogrenci_item)
        
        layout.addWidget(self.table)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        # Excel button
        excel_btn = QPushButton("📊 Excel İndir")
        excel_btn.setFixedHeight(44)
        excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 8px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        excel_btn.clicked.connect(self.export_excel)
        
        # PDF button
        pdf_btn = QPushButton("📄 PDF İndir")
        pdf_btn.setFixedHeight(44)
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 8px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        pdf_btn.clicked.connect(self.export_pdf)
        
        # Save button
        save_btn = QPushButton("💾 Veritabanına Kaydet")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 8px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
        """)
        save_btn.clicked.connect(self.save_to_db)
        
        # Close button
        close_btn = QPushButton("❌ Kapat (İptal)")
        close_btn.setFixedHeight(44)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 8px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        close_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(excel_btn)
        btn_layout.addWidget(pdf_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def export_excel(self):
        """Export to Excel"""
        try:
            default_name = f"sinav_programi_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Excel Dosyası Kaydet",
                default_name,
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # Get department info
            bolum_query = "SELECT bolum_adi FROM bolumler WHERE bolum_id = %s"
            bolum_result = db.execute_query(bolum_query, (self.bolum_id,))
            bolum_adi = bolum_result[0]['bolum_adi'] if bolum_result else "BÖLÜM"
            
            sinav_tipi = self.params.get('sinav_tipi', 'SINAV')
            
            data = {
                'type': 'sinav_takvimi',
                'title': 'Sınav Programı',
                'bolum_adi': bolum_adi,
                'sinav_tipi': sinav_tipi,
                'data': self.schedule_data,
                'bolum_id': self.bolum_id
            }
            
            success = ExportUtils.export_to_excel(data, file_path)
            
            if success:
                QMessageBox.information(self, "Başarılı", f"✅ Excel dosyası oluşturuldu!\n\n{file_path}")
            else:
                QMessageBox.warning(self, "Hata", "Excel dosyası oluşturulamadı!")
                
        except Exception as e:
            logger.error(f"Excel export error: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Excel'e aktarırken hata:\n{str(e)}")
    
    def export_pdf(self):
        """Export to PDF"""
        try:
            default_name = f"sinav_programi_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "PDF Dosyası Kaydet",
                default_name,
                "PDF Files (*.pdf)"
            )
            
            if not file_path:
                return
            
            # Get department info
            bolum_query = "SELECT bolum_adi FROM bolumler WHERE bolum_id = %s"
            bolum_result = db.execute_query(bolum_query, (self.bolum_id,))
            bolum_adi = bolum_result[0]['bolum_adi'] if bolum_result else "BÖLÜM"
            
            sinav_tipi = self.params.get('sinav_tipi', 'SINAV')
            
            data = {
                'type': 'sinav_takvimi',
                'title': 'Sınav Programı',
                'bolum_adi': bolum_adi,
                'sinav_tipi': sinav_tipi,
                'data': self.schedule_data,
                'bolum_id': self.bolum_id,
                'options': {}
            }
            
            success = ExportUtils.export_to_pdf(data, file_path)
            
            if success:
                QMessageBox.information(self, "Başarılı", f"✅ PDF dosyası oluşturuldu!\n\n{file_path}")
            else:
                QMessageBox.warning(self, "Hata", "PDF dosyası oluşturulamadı!")
                
        except Exception as e:
            logger.error(f"PDF export error: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"PDF'e aktarırken hata:\n{str(e)}")
    
    def save_to_db(self):
        """Save schedule to database"""
        reply = QMessageBox.question(
            self,
            "Veritabanına Kaydet",
            f"Sınav programını veritabanına kaydetmek istediğinizden emin misiniz?\n\n"
            f"📊 {len(self.schedule_data)} kayıt eklenecek.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            try:
                sinav_model = SinavModel(db)
                ders_model = DersModel(db)
                derslik_model = DerslikModel(db)
                sinav_controller = SinavController(sinav_model, ders_model, derslik_model)
                
                result = sinav_controller.save_exam_schedule(self.schedule_data)
                
                if result['success']:
                    QMessageBox.information(self, "Başarılı", "✅ " + result['message'])
                    self.accept()  # Close dialog after successful save
                else:
                    QMessageBox.warning(self, "Hata", result['message'])
                    
            except Exception as e:
                logger.error(f"Save error: {e}", exc_info=True)
                QMessageBox.critical(self, "Hata", f"Kayıt sırasında hata:\n{str(e)}")


class SinavOlusturView(QWidget):
    """Modern exam schedule creation view"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id', 1)
        
        self.sinav_model = SinavModel(db)
        self.ders_model = DersModel(db)
        self.derslik_model = DerslikModel(db)
        self.ogrenci_model = OgrenciModel(db)
        
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        title = QLabel("📅 Sınav Programı Yönetimi")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabBar::tab {
                padding: 8px 16px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                color: #3b82f6;
                border-bottom: 2px solid #3b82f6;
            }
        """)
        
        # Tab 1: Existing Programs
        self.programs_tab = QWidget()
        self.setup_programs_tab()
        self.tab_widget.addTab(self.programs_tab, "📋 Mevcut Programlar")
        
        # Tab 2: Create New Program
        self.create_tab = QWidget()
        self.setup_create_tab()
        self.tab_widget.addTab(self.create_tab, "➕ Yeni Program Oluştur")
        
        layout.addWidget(self.tab_widget)
    
    def setup_programs_tab(self):
        """Setup existing programs tab"""
        layout = QVBoxLayout(self.programs_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        info = QLabel("Kayıtlı sınav programlarınızı görüntüleyin, indirin veya silin")
        info.setStyleSheet("color: #6b7280; font-size: 13px;")
        
        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #374151;
                font-weight: bold;
                border-radius: 8px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        refresh_btn.clicked.connect(self.load_existing_programs)
        
        toolbar.addWidget(info)
        toolbar.addStretch()
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)
        
        # Programs table
        self.programs_table = QTableWidget()
        self.programs_table.setColumnCount(6)
        self.programs_table.setHorizontalHeaderLabels([
            "Program Adı", "Sınav Tipi", "Başlangıç", "Bitiş", "Sınav Sayısı", "İşlemler"
        ])
        self.programs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.programs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.programs_table.setAlternatingRowColors(True)
        self.programs_table.verticalHeader().setVisible(False)
        
        # Column widths - responsive
        header = self.programs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        
        layout.addWidget(self.programs_table)
        
        # Load programs
        self.load_existing_programs()
    
    def setup_create_tab(self):
        """Setup create new program tab"""
        layout = QVBoxLayout(self.create_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Two column layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(15)
        
        # LEFT COLUMN
        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        
        # Basic info
        basic_group = QGroupBox("Temel Bilgiler")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(8)
        
        self.sinav_tipi_combo = QComboBox()
        self.sinav_tipi_combo.addItems(["Vize", "Final", "Bütünleme"])
        self.sinav_tipi_combo.setFixedHeight(35)
        basic_layout.addRow("Sınav Tipi:", self.sinav_tipi_combo)
        
        self.baslangic_tarih = QDateTimeEdit()
        self.baslangic_tarih.setDateTime(QDateTime.currentDateTime().addDays(7))
        self.baslangic_tarih.setCalendarPopup(True)
        self.baslangic_tarih.setDisplayFormat("dd.MM.yyyy")
        self.baslangic_tarih.setFixedHeight(35)
        basic_layout.addRow("Başlangıç Tarihi:", self.baslangic_tarih)
        
        self.bitis_tarih = QDateTimeEdit()
        self.bitis_tarih.setDateTime(QDateTime.currentDateTime().addDays(14))
        self.bitis_tarih.setCalendarPopup(True)
        self.bitis_tarih.setDisplayFormat("dd.MM.yyyy")
        self.bitis_tarih.setFixedHeight(35)
        basic_layout.addRow("Bitiş Tarihi:", self.bitis_tarih)
        
        self.sinav_suresi = QSpinBox()
        self.sinav_suresi.setRange(1, 999)
        self.sinav_suresi.setValue(75)
        self.sinav_suresi.setSuffix(" dk")
        self.sinav_suresi.setFixedHeight(35)
        self.sinav_suresi.valueChanged.connect(self.update_all_course_durations)
        basic_layout.addRow("Varsayılan Sınav Süresi:", self.sinav_suresi)
        
        self.ara_suresi = QSpinBox()
        self.ara_suresi.setRange(5, 60)
        self.ara_suresi.setValue(15)
        self.ara_suresi.setSuffix(" dk")
        self.ara_suresi.setFixedHeight(35)
        basic_layout.addRow("Bekleme Süresi:", self.ara_suresi)
        
        left_col.addWidget(basic_group)
        
        # Constraints group
        constraints_group = QGroupBox("Kısıtlamalar")
        constraints_layout = QVBoxLayout(constraints_group)
        constraints_layout.setSpacing(10)
        
        self.ayni_anda_sinav_checkbox = QCheckBox("Sınavlar aynı zamana denk gelmesin")
        self.ayni_anda_sinav_checkbox.setToolTip("Bir sınav başladığında, o sınav bitene kadar başka sınav başlamaz")
        constraints_layout.addWidget(self.ayni_anda_sinav_checkbox)
        
        gunluk_limit_layout = QHBoxLayout()
        gunluk_limit_label = QLabel("Günlük sınav limiti (sınıf başına):")
        self.gunluk_sinav_limiti = QSpinBox()
        self.gunluk_sinav_limiti.setRange(1, 10)
        self.gunluk_sinav_limiti.setValue(3)
        self.gunluk_sinav_limiti.setFixedHeight(35)
        self.gunluk_sinav_limiti.setToolTip("Bir sınıf için günde maksimum kaç sınav olabilir")
        gunluk_limit_layout.addWidget(gunluk_limit_label)
        gunluk_limit_layout.addWidget(self.gunluk_sinav_limiti)
        gunluk_limit_layout.addStretch()
        constraints_layout.addLayout(gunluk_limit_layout)
        
        left_col.addWidget(constraints_group)
        
        # Time settings
        time_group = QGroupBox("Saat Ayarları")
        time_layout = QFormLayout(time_group)
        time_layout.setSpacing(8)
        
        # First exam
        first_layout = QHBoxLayout()
        self.ilk_sinav_saat = QSpinBox()
        self.ilk_sinav_saat.setRange(0, 23)
        self.ilk_sinav_saat.setValue(10)
        self.ilk_sinav_saat.setFixedHeight(35)
        self.ilk_sinav_dakika = QSpinBox()
        self.ilk_sinav_dakika.setRange(0, 59)
        self.ilk_sinav_dakika.setValue(0)
        self.ilk_sinav_dakika.setFixedHeight(35)
        first_layout.addWidget(self.ilk_sinav_saat)
        first_layout.addWidget(QLabel(":"))
        first_layout.addWidget(self.ilk_sinav_dakika)
        first_layout.addStretch()
        time_layout.addRow("İlk Sınav:", first_layout)
        
        # Last exam
        last_layout = QHBoxLayout()
        self.son_sinav_saat = QSpinBox()
        self.son_sinav_saat.setRange(0, 23)
        self.son_sinav_saat.setValue(19)
        self.son_sinav_saat.setFixedHeight(35)
        self.son_sinav_dakika = QSpinBox()
        self.son_sinav_dakika.setRange(0, 59)
        self.son_sinav_dakika.setValue(15)
        self.son_sinav_dakika.setFixedHeight(35)
        last_layout.addWidget(self.son_sinav_saat)
        last_layout.addWidget(QLabel(":"))
        last_layout.addWidget(self.son_sinav_dakika)
        last_layout.addStretch()
        time_layout.addRow("Son Sınav:", last_layout)
        
        # Lunch start
        lunch_start_layout = QHBoxLayout()
        self.ogle_baslangic_saat = QSpinBox()
        self.ogle_baslangic_saat.setRange(0, 23)
        self.ogle_baslangic_saat.setValue(12)
        self.ogle_baslangic_saat.setFixedHeight(35)
        self.ogle_baslangic_dakika = QSpinBox()
        self.ogle_baslangic_dakika.setRange(0, 59)
        self.ogle_baslangic_dakika.setValue(0)
        self.ogle_baslangic_dakika.setFixedHeight(35)
        lunch_start_layout.addWidget(self.ogle_baslangic_saat)
        lunch_start_layout.addWidget(QLabel(":"))
        lunch_start_layout.addWidget(self.ogle_baslangic_dakika)
        lunch_start_layout.addStretch()
        time_layout.addRow("Öğle Başlangıç:", lunch_start_layout)
        
        # Lunch end
        lunch_end_layout = QHBoxLayout()
        self.ogle_bitis_saat = QSpinBox()
        self.ogle_bitis_saat.setRange(0, 23)
        self.ogle_bitis_saat.setValue(13)
        self.ogle_bitis_saat.setFixedHeight(35)
        self.ogle_bitis_dakika = QSpinBox()
        self.ogle_bitis_dakika.setRange(0, 59)
        self.ogle_bitis_dakika.setValue(0)
        self.ogle_bitis_dakika.setFixedHeight(35)
        lunch_end_layout.addWidget(self.ogle_bitis_saat)
        lunch_end_layout.addWidget(QLabel(":"))
        lunch_end_layout.addWidget(self.ogle_bitis_dakika)
        lunch_end_layout.addStretch()
        time_layout.addRow("Öğle Bitiş:", lunch_end_layout)
        
        left_col.addWidget(time_group)
        
        # Days selection
        days_group = QGroupBox("Sınav Günleri")
        days_layout = QVBoxLayout(days_group)
        days_layout.setSpacing(6)
        
        self.gun_checkboxes = {}
        gun_isimleri = {
            0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 
            4: "Cuma", 5: "Cumartesi", 6: "Pazar"
        }
        
        for day_num, day_name in gun_isimleri.items():
            checkbox = QCheckBox(day_name)
            if day_num < 5:
                checkbox.setChecked(True)
            self.gun_checkboxes[day_num] = checkbox
            days_layout.addWidget(checkbox)
        
        left_col.addWidget(days_group)
        left_col.addStretch()
        main_layout.addLayout(left_col, 1)
        
        # RIGHT COLUMN - Course selection
        right_col = QVBoxLayout()
        right_col.setSpacing(12)
        
        course_group = QGroupBox("Ders Seçimi")
        course_layout = QVBoxLayout(course_group)
        course_layout.setSpacing(8)
        
        # Info
        info_label = QLabel("✓ Tüm dersler listelenir. Sınava dahil olmayanları işaretini kaldırın.")
        info_label.setStyleSheet("color: #6b7280; font-size: 11px; padding: 4px;")
        course_layout.addWidget(info_label)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.ders_search = QLineEdit()
        self.ders_search.setPlaceholderText("Ders ara...")
        self.ders_search.setFixedHeight(35)
        self.ders_search.textChanged.connect(self.filter_courses)
        toolbar.addWidget(self.ders_search, 1)
        
        select_all_btn = QPushButton("Tümünü Seç")
        select_all_btn.setFixedHeight(35)
        select_all_btn.clicked.connect(self.select_all_courses)
        toolbar.addWidget(select_all_btn)
        
        clear_all_btn = QPushButton("Temizle")
        clear_all_btn.setFixedHeight(35)
        clear_all_btn.clicked.connect(self.clear_all_courses)
        toolbar.addWidget(clear_all_btn)
        
        check_parallel_btn = QPushButton("🔍 Ortak Öğrenciler")
        check_parallel_btn.setFixedHeight(35)
        check_parallel_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                border-radius: 4px;
                padding: 0 12px;
            }
            QPushButton:hover { background: #2563eb; }
        """)
        check_parallel_btn.setToolTip("Hangi dersler aynı anda yapılabilir?")
        check_parallel_btn.clicked.connect(self.show_parallel_exams)
        toolbar.addWidget(check_parallel_btn)
        
        course_layout.addLayout(toolbar)
        
        # Course list with durations
        course_scroll = QScrollArea()
        course_scroll.setWidgetResizable(True)
        
        self.ders_container = QWidget()
        self.ders_container_layout = QVBoxLayout(self.ders_container)
        self.ders_container_layout.setSpacing(4)
        self.ders_checkboxes = {}
        self.ders_duration_spinboxes = {}  # Store custom durations
        
        course_scroll.setWidget(self.ders_container)
        course_layout.addWidget(course_scroll)
        
        # Stats
        self.ders_stats_label = QLabel("Yükleniyor...")
        self.ders_stats_label.setStyleSheet("color: #6b7280; font-size: 12px; padding: 4px;")
        course_layout.addWidget(self.ders_stats_label)
        
        right_col.addWidget(course_group)
        main_layout.addLayout(right_col, 2)
        
        layout.addLayout(main_layout)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(30)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        self.progress_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_label)
        
        # Create button
        self.create_btn = QPushButton("🚀 Program Oluştur")
        self.create_btn.setMinimumHeight(42)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background: #10b981;
                color: white;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #059669; }
            QPushButton:disabled { background: #d1d5db; color: #9ca3af; }
        """)
        self.create_btn.clicked.connect(self.create_schedule)
        layout.addWidget(self.create_btn)
    
    def load_existing_programs(self):
        """Load and display existing programs"""
        try:
            programs = self.sinav_model.get_programs_by_bolum(self.bolum_id)
            
            self.programs_table.setRowCount(0)
            
            for program in programs:
                row = self.programs_table.rowCount()
                self.programs_table.insertRow(row)
                self.programs_table.setRowHeight(row, 50)
                
                sinavlar = self.sinav_model.get_sinavlar_by_program(program['program_id'])
                exam_count = len(sinavlar)
                
                self.programs_table.setItem(row, 0, QTableWidgetItem(program['program_adi']))
                self.programs_table.setItem(row, 1, QTableWidgetItem(program.get('sinav_tipi', 'Final')))
                self.programs_table.setItem(row, 2, QTableWidgetItem(str(program.get('baslangic_tarihi', ''))))
                self.programs_table.setItem(row, 3, QTableWidgetItem(str(program.get('bitis_tarihi', ''))))
                
                count_item = QTableWidgetItem(str(exam_count))
                count_item.setTextAlignment(Qt.AlignCenter)
                self.programs_table.setItem(row, 4, count_item)
                
                # Action buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(8, 4, 8, 4)
                actions_layout.setSpacing(8)
                
                view_btn = QPushButton("📋 Görüntüle")
                view_btn.setFixedHeight(36)
                view_btn.setMinimumWidth(95)
                view_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #6366f1;
                        color: white;
                        font-weight: bold;
                        border-radius: 6px;
                        padding: 4px 12px;
                    }
                    QPushButton:hover {
                        background-color: #4f46e5;
                    }
                """)
                view_btn.clicked.connect(lambda checked=False, p=dict(program): self.view_program(p))
                
                excel_btn = QPushButton("📊 Excel")
                excel_btn.setFixedHeight(36)
                excel_btn.setMinimumWidth(85)
                excel_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #10b981;
                        color: white;
                        font-weight: bold;
                        border-radius: 6px;
                        padding: 4px 12px;
                    }
                    QPushButton:hover {
                        background-color: #059669;
                    }
                """)
                excel_btn.clicked.connect(lambda checked=False, p=dict(program): self.export_program_excel(p))
                
                pdf_btn = QPushButton("📄 PDF")
                pdf_btn.setFixedHeight(36)
                pdf_btn.setMinimumWidth(75)
                pdf_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3b82f6;
                        color: white;
                        font-weight: bold;
                        border-radius: 6px;
                        padding: 4px 12px;
                    }
                    QPushButton:hover {
                        background-color: #2563eb;
                    }
                """)
                pdf_btn.clicked.connect(lambda checked=False, p=dict(program): self.export_program_pdf(p))
                
                delete_btn = QPushButton("🗑️ Sil")
                delete_btn.setFixedHeight(36)
                delete_btn.setMinimumWidth(70)
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ef4444;
                        color: white;
                        font-weight: bold;
                        border-radius: 6px;
                        padding: 4px 12px;
                    }
                    QPushButton:hover {
                        background-color: #dc2626;
                    }
                """)
                delete_btn.clicked.connect(lambda checked=False, p=dict(program): self.delete_program(p))
                
                # Class-based report button
                class_report_btn = QPushButton("🎓 Sınıf Bazlı")
                class_report_btn.setFixedHeight(36)
                class_report_btn.setMinimumWidth(105)
                class_report_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #8b5cf6;
                        color: white;
                        font-weight: bold;
                        border-radius: 6px;
                        padding: 4px 12px;
                    }
                    QPushButton:hover {
                        background-color: #7c3aed;
                    }
                """)
                class_report_btn.clicked.connect(lambda checked=False, p=dict(program): self.export_class_based_report(p))
                
                actions_layout.addWidget(view_btn)
                actions_layout.addWidget(excel_btn)
                actions_layout.addWidget(pdf_btn)
                actions_layout.addWidget(class_report_btn)
                actions_layout.addWidget(delete_btn)
                actions_layout.addStretch()
                
                self.programs_table.setCellWidget(row, 5, actions_widget)
            
            logger.info(f"Loaded {len(programs)} exam programs")
            
        except Exception as e:
            logger.error(f"Error loading programs: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Programlar yüklenirken hata:\n{str(e)}")
    
    def view_program(self, program):
        """View program details in a dialog"""
        try:
            sinavlar = self.sinav_model.get_sinavlar_by_program(program['program_id'])
            
            if not sinavlar:
                QMessageBox.information(self, "Bilgi", "Bu programda henüz sınav yok!")
                return
            
            from PySide6.QtWidgets import QDialog, QVBoxLayout
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"📅 {program['program_adi']} - Program Detayları")
            dialog.setMinimumSize(900, 600)
            
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(16)
            
            # Info header
            info_label = QLabel(
                f"📝 Tip: {program.get('sinav_tipi', 'Final')}  |  "
                f"📆 {program.get('baslangic_tarihi')} - {program.get('bitis_tarihi')}  |  "
                f"📊 Toplam {len(sinavlar)} sınav"
            )
            info_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; padding: 10px; background: #f3f4f6; border-radius: 8px;")
            layout.addWidget(info_label)
            
            # Table - ADD SINIF COLUMN
            table = QTableWidget()
            table.setColumnCount(7)  # Added one more column for Sınıf
            table.setHorizontalHeaderLabels(['Tarih/Saat', 'Ders Kodu', 'Ders Adı', 'Sınıf', 'Öğretim Elemanı', 'Derslik', 'Öğrenci'])
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setVisible(False)
            
            # Column widths
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Sınıf
            header.setSectionResizeMode(4, QHeaderView.Stretch)
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
            
            # Populate table
            for sinav in sinavlar:
                row = table.rowCount()
                table.insertRow(row)
                
                tarih = datetime.fromisoformat(sinav['tarih_saat']) if isinstance(sinav['tarih_saat'], str) else sinav['tarih_saat']
                tarih_str = tarih.strftime("%d.%m.%Y %H:%M")
                
                # Get sınıf info from ders
                ders = self.ders_model.get_ders_by_id(sinav['ders_id'])
                sinif_str = f"{ders.get('sinif', '?')}. Sınıf" if ders else "?"
                
                table.setItem(row, 0, QTableWidgetItem(tarih_str))
                table.setItem(row, 1, QTableWidgetItem(sinav.get('ders_kodu', '')))
                table.setItem(row, 2, QTableWidgetItem(sinav.get('ders_adi', '')))
                table.setItem(row, 3, QTableWidgetItem(sinif_str))  # NEW: Sınıf column
                table.setItem(row, 4, QTableWidgetItem(sinav.get('ogretim_elemani', '')))
                table.setItem(row, 5, QTableWidgetItem(sinav.get('derslik_adi', sinav.get('derslik_kodu', ''))))
                
                ogrenci_item = QTableWidgetItem(str(sinav.get('ogrenci_sayisi', 0)))
                ogrenci_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 6, ogrenci_item)  # Column 6 for Öğrenci
            
            layout.addWidget(table)
            
            # Close button
            close_btn = QPushButton("✅ Kapat")
            close_btn.setFixedHeight(40)
            close_btn.setFixedWidth(120)
            close_btn.clicked.connect(dialog.accept)
            
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            btn_layout.addWidget(close_btn)
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error viewing program: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Program görüntülenirken hata:\n{str(e)}")
    
    def delete_program(self, program):
        """Delete a program"""
        reply = QMessageBox.question(
            self,
            "Programı Sil",
            f"'{program['program_adi']}' programını silmek istediğinizden emin misiniz?\n\n"
            f"Bu işlem geri alınamaz ve programa ait tüm sınavlar silinecektir!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                result = self.sinav_model.delete_program(program['program_id'])
                
                if result:
                    QMessageBox.information(self, "Başarılı", "Program başarıyla silindi!")
                    self.load_existing_programs()
                else:
                    QMessageBox.warning(self, "Uyarı", "Program silinemedi!")
                    
            except Exception as e:
                logger.error(f"Error deleting program: {e}", exc_info=True)
                QMessageBox.critical(self, "Hata", f"Program silinirken hata:\n{str(e)}")
    
    def export_program_excel(self, program):
        """Export program to Excel"""
        try:
            sinavlar = self.sinav_model.get_sinavlar_by_program(program['program_id'])
            
            if not sinavlar:
                QMessageBox.information(self, "Bilgi", "Bu programda henüz sınav yok!")
                return
            
            # Ask for save location
            default_name = f"sinav_programi_{program['program_adi']}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Excel Dosyası Kaydet",
                default_name,
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # Get department info
            bolum_query = "SELECT bolum_adi FROM bolumler WHERE bolum_id = %s"
            bolum_result = db.execute_query(bolum_query, (self.bolum_id,))
            bolum_adi = bolum_result[0]['bolum_adi'] if bolum_result else "BÖLÜM"
            sinav_tipi = program.get('sinav_tipi', 'SINAV')
            
            data = {
                'type': 'sinav_takvimi',
                'title': 'Sınav Programı',
                'bolum_adi': bolum_adi,
                'sinav_tipi': sinav_tipi,
                'data': sinavlar,
                'bolum_id': self.bolum_id
            }
            
            success = ExportUtils.export_to_excel(data, file_path)
            
            if success:
                QMessageBox.information(self, "Başarılı", f"✅ Excel dosyası oluşturuldu!\n\n{file_path}")
            else:
                QMessageBox.warning(self, "Hata", "Excel dosyası oluşturulamadı!")
            
        except Exception as e:
            logger.error(f"Error exporting program to Excel: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Excel'e aktarırken hata:\n{str(e)}")
    
    def export_program_pdf(self, program):
        """Export program to PDF using ExportUtils"""
        try:
            sinavlar = self.sinav_model.get_sinavlar_by_program(program['program_id'])
            
            if not sinavlar:
                QMessageBox.information(self, "Bilgi", "Bu programda henüz sınav yok!")
                return
            
            # Get department info
            bolum_query = "SELECT bolum_adi FROM bolumler WHERE bolum_id = %s"
            bolum_result = db.execute_query(bolum_query, (self.bolum_id,))
            bolum_adi = bolum_result[0]['bolum_adi'] if bolum_result else "BÖLÜM"
            sinav_tipi = program.get('sinav_tipi', 'SINAV')
            
            # Ask for save location
            default_name = f"sinav_programi_{program['program_adi']}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "PDF Dosyası Kaydet",
                default_name,
                "PDF Files (*.pdf)"
            )
            
            if not file_path:
                return
            
            data = {
                'type': 'sinav_takvimi',
                'title': 'Sınav Programı',
                'bolum_adi': bolum_adi,
                'sinav_tipi': sinav_tipi,
                'data': sinavlar,
                'bolum_id': self.bolum_id,
                'options': {}
            }
            
            success = ExportUtils.export_to_pdf(data, file_path)
            
            if success:
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"✅ Sınav programı PDF'e aktarıldı!\n\nDosya: {file_path}"
                )
            else:
                QMessageBox.warning(self, "Uyarı", "PDF oluşturulamadı!")
            
        except Exception as e:
            logger.error(f"Error exporting program to PDF: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"PDF'e aktarırken hata:\n{str(e)}")
    
    def export_class_based_report(self, program):
        """Export class-based exam schedule (both Excel and PDF)"""
        try:
            from collections import defaultdict
            from PySide6.QtWidgets import QFileDialog
            import os
            from datetime import datetime
            
            sinavlar = self.sinav_model.get_sinavlar_by_program(program['program_id'])
            
            if not sinavlar:
                QMessageBox.information(self, "Bilgi", "Bu programda henüz sınav yok!")
                return
            
            logger.info(f"📚 Total exams in program: {len(sinavlar)}")
            
            # Group by class
            sinav_by_class = defaultdict(list)
            for sinav in sinavlar:
                # Fetch course to get class info
                ders = self.ders_model.get_ders_by_id(sinav['ders_id'])
                if ders:
                    sinif = ders.get('sinif', 0)
                    sinav_with_class = sinav.copy()
                    sinav_with_class['sinif'] = sinif
                    sinav_by_class[sinif].append(sinav_with_class)
                    
                    # Log sample data
                    if len(sinav_by_class[sinif]) == 1:  # First exam of this class
                        logger.info(f"   Class {sinif} - {ders['ders_kodu']}: {sinav['tarih']} {sinav['baslangic_saati']}")
            
            if not sinav_by_class:
                QMessageBox.warning(self, "Uyarı", "Sınıf bilgisi bulunamadı!")
                return
            
            # Create selection dialog
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QGroupBox
            
            choice_dialog = QDialog(self)
            choice_dialog.setWindowTitle("Sınıf Bazlı Rapor")
            choice_dialog.setMinimumWidth(500)
            choice_dialog.setMinimumHeight(450)
            choice_layout = QVBoxLayout(choice_dialog)
            
            # Header
            header = QLabel("📊 Sınıf Bazlı Rapor Oluştur")
            header.setFont(QFont("Segoe UI", 14, QFont.Bold))
            header.setStyleSheet("padding: 10px; color: #1f2937;")
            choice_layout.addWidget(header)
            
            info = QLabel(f"Raporlanacak sınıfları ve formatı seçin:")
            info.setStyleSheet("padding: 5px 10px; font-size: 12px; color: #6b7280;")
            choice_layout.addWidget(info)
            
            # Class selection group
            class_group = QGroupBox("Sınıf Seçimi")
            class_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #e5e7eb;
                    border-radius: 8px;
                    margin-top: 12px;
                    padding-top: 15px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
            """)
            class_layout = QVBoxLayout(class_group)
            class_layout.setSpacing(8)
            
            # Add "Select All" button
            select_buttons = QHBoxLayout()
            select_all_btn = QPushButton("✓ Tümünü Seç")
            select_all_btn.setFixedHeight(30)
            select_all_btn.setStyleSheet("""
                QPushButton {
                    background: #e5e7eb;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                }
                QPushButton:hover { background: #d1d5db; }
            """)
            
            clear_all_btn = QPushButton("✗ Temizle")
            clear_all_btn.setFixedHeight(30)
            clear_all_btn.setStyleSheet("""
                QPushButton {
                    background: #e5e7eb;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                }
                QPushButton:hover { background: #d1d5db; }
            """)
            select_buttons.addWidget(select_all_btn)
            select_buttons.addWidget(clear_all_btn)
            select_buttons.addStretch()
            class_layout.addLayout(select_buttons)
            
            # Create checkboxes for each class
            class_checkboxes = {}
            for sinif in sorted(sinav_by_class.keys()):
                exam_count = len(sinav_by_class[sinif])
                cb = QCheckBox(f"📚 {sinif}. Sınıf ({exam_count} sınav)")
                cb.setChecked(True)
                cb.setStyleSheet("""
                    QCheckBox {
                        padding: 8px;
                        font-size: 13px;
                    }
                    QCheckBox::indicator {
                        width: 20px;
                        height: 20px;
                    }
                """)
                class_checkboxes[sinif] = cb
                class_layout.addWidget(cb)
            
            # Connect select all buttons
            select_all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in class_checkboxes.values()])
            clear_all_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in class_checkboxes.values()])
            
            choice_layout.addWidget(class_group)
            
            # Format selection group
            format_group = QGroupBox("Format Seçimi")
            format_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #e5e7eb;
                    border-radius: 8px;
                    margin-top: 12px;
                    padding-top: 15px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
            """)
            format_layout = QHBoxLayout(format_group)
            format_layout.setSpacing(10)
            
            excel_btn = QPushButton("📊 Excel")
            excel_btn.setFixedHeight(40)
            excel_btn.setStyleSheet("""
                QPushButton {
                    background: #10b981;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                QPushButton:hover { background: #059669; }
            """)
            excel_btn.clicked.connect(lambda: choice_dialog.done(1))
            
            pdf_btn = QPushButton("📄 PDF")
            pdf_btn.setFixedHeight(40)
            pdf_btn.setStyleSheet("""
                QPushButton {
                    background: #3b82f6;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                QPushButton:hover { background: #2563eb; }
            """)
            pdf_btn.clicked.connect(lambda: choice_dialog.done(2))
            
            both_btn = QPushButton("📁 Her İkisi")
            both_btn.setFixedHeight(40)
            both_btn.setStyleSheet("""
                QPushButton {
                    background: #8b5cf6;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                QPushButton:hover { background: #7c3aed; }
            """)
            both_btn.clicked.connect(lambda: choice_dialog.done(3))
            
            format_layout.addWidget(excel_btn)
            format_layout.addWidget(pdf_btn)
            format_layout.addWidget(both_btn)
            
            choice_layout.addWidget(format_group)
            
            # Bottom buttons
            bottom_layout = QHBoxLayout()
            bottom_layout.addStretch()
            
            cancel_btn = QPushButton("İptal")
            cancel_btn.setFixedHeight(36)
            cancel_btn.setFixedWidth(100)
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background: #ef4444;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                }
                QPushButton:hover { background: #dc2626; }
            """)
            cancel_btn.clicked.connect(choice_dialog.reject)
            bottom_layout.addWidget(cancel_btn)
            
            choice_layout.addLayout(bottom_layout)
            
            result = choice_dialog.exec()
            
            if result == 0:  # Cancelled
                return
            
            # Get selected classes
            selected_classes = [sinif for sinif, cb in class_checkboxes.items() if cb.isChecked()]
            
            if not selected_classes:
                QMessageBox.warning(self, "Uyarı", "En az bir sınıf seçmelisiniz!")
                return
            
            # Ask for directory to save files
            save_dir = QFileDialog.getExistingDirectory(
                self,
                "Raporları Kaydetmek İçin Klasör Seçin",
                "",
                QFileDialog.ShowDirsOnly
            )
            
            if not save_dir:
                return
            
            # Create separate files for selected classes
            success_count = 0
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            created_files = []
            
            for sinif in sorted(selected_classes):
                class_sinavlar = sinav_by_class[sinif]
                
                # Sort by date and time
                class_sinavlar.sort(key=lambda x: (x['tarih'], x['baslangic_saati']))
                
                # Log all exams for this class to debug
                logger.info(f"📋 Class {sinif} - {len(class_sinavlar)} exams:")
                for idx, exam in enumerate(class_sinavlar[:5]):  # Show first 5
                    logger.info(f"   [{idx+1}] {exam.get('ders_kodu')}")
                    logger.info(f"        tarih: {exam.get('tarih')}")
                    logger.info(f"        baslangic_saati: {exam.get('baslangic_saati')}")
                    logger.info(f"        tarih_saat (STRING): {exam.get('tarih_saat')}")
                
                # Use the data AS IS from database - don't modify tarih_saat!
                # The export utilities handle the tarih_saat parsing internally
                logger.info(f"📊 Class {sinif}: {len(class_sinavlar)} exams will be exported")
                
                title = f"{program['program_adi']} - {sinif}. Sınıf"
                
                # Get bolum_adi from user_data or database
                bolum_adi = self.user_data.get('bolum_adi', '')
                if not bolum_adi:
                    # Try to get from database if not in user_data
                    try:
                        from models.bolum_model import BolumModel
                        bolum_model = BolumModel(db)
                        bolum = bolum_model.get_bolum_by_id(self.bolum_id)
                        bolum_adi = bolum.get('bolum_adi', '') if bolum else ''
                    except:
                        bolum_adi = ''
                
                # Convert to format expected by ExportUtils
                # Use class_sinavlar directly - same format as normal export
                export_data = {
                    'type': 'sinav_takvimi',  # Same type as normal export
                    'title': title,
                    'data': class_sinavlar,  # Use original data from database
                    'bolum_adi': bolum_adi,
                    'sinav_tipi': program.get('sinav_tipi', 'Final'),
                    'bolum_id': self.bolum_id,
                    'options': {}
                }
                
                # Excel export
                if result in [1, 3]:
                    filename = os.path.join(
                        save_dir,
                        f"sinav_programi_{sinif}_sinif_{timestamp}.xlsx"
                    )
                    
                    if ExportUtils.export_to_excel(export_data, filename):
                        success_count += 1
                        created_files.append(os.path.basename(filename))
                        logger.info(f"Class {sinif} exported to Excel: {filename}")
                
                # PDF export
                if result in [2, 3]:
                    filename = os.path.join(
                        save_dir,
                        f"sinav_programi_{sinif}_sinif_{timestamp}.pdf"
                    )
                    
                    if ExportUtils.export_to_pdf(export_data, filename):
                        success_count += 1
                        created_files.append(os.path.basename(filename))
                        logger.info(f"Class {sinif} exported to PDF: {filename}")
            
            if success_count > 0:
                files_list = "\n".join([f"  • {f}" for f in created_files])
                class_names = ", ".join([f"{s}. Sınıf" for s in sorted(selected_classes)])
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"✅ Sınıf bazlı raporlar başarıyla oluşturuldu!\n\n"
                    f"Seçilen Sınıflar: {class_names}\n"
                    f"Klasör: {save_dir}\n\n"
                    f"Oluşturulan dosyalar ({success_count}):\n{files_list}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Uyarı",
                    "❌ Hiçbir dosya oluşturulamadı!\n\nLütfen log dosyasını kontrol edin."
                )
            
        except Exception as e:
            logger.error(f"Error exporting class-based report: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Sınıf bazlı rapor oluşturulurken hata:\n{str(e)}")
    
    def _get_day_name(self, date):
        """Get Turkish day name from date"""
        from datetime import datetime, date as date_type
        
        days = {
            0: "Pazartesi",
            1: "Salı",
            2: "Çarşamba",
            3: "Perşembe",
            4: "Cuma",
            5: "Cumartesi",
            6: "Pazar"
        }
        
        try:
            # If it's already a date or datetime object
            if hasattr(date, 'weekday'):
                return days.get(date.weekday(), str(date))
            
            # If it's a string, try to parse it
            if isinstance(date, str):
                try:
                    parsed_date = datetime.strptime(date, '%Y-%m-%d')
                    return days.get(parsed_date.weekday(), date)
                except:
                    try:
                        parsed_date = datetime.strptime(date, '%d.%m.%Y')
                        return days.get(parsed_date.weekday(), date)
                    except:
                        pass
            
            return str(date)
        except Exception as e:
            logger.error(f"Error getting day name for date {date}: {e}")
            return str(date)
    
    def load_data(self):
        """Load necessary data"""
        try:
            dersler = self.ders_model.get_dersler_by_bolum(self.bolum_id)
            derslikler = self.derslik_model.get_derslikler_by_bolum(self.bolum_id)
            
            if not dersler:
                QMessageBox.warning(self, "Uyarı", "Henüz ders tanımlanmamış!")
                return
            
            if not derslikler:
                QMessageBox.warning(self, "Uyarı", "Henüz derslik tanımlanmamış!")
                return
            
            self.populate_course_list(dersler)
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def populate_course_list(self, dersler):
        """Populate course selection checkboxes with custom duration"""
        while self.ders_container_layout.count():
            item = self.ders_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.ders_checkboxes.clear()
        self.ders_duration_spinboxes.clear()
        
        for ders in dersler:
            # Create row widget
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            
            # Checkbox
            checkbox = QCheckBox(f"{ders['ders_kodu']} - {ders['ders_adi']}")
            checkbox.setChecked(True)
            checkbox.setProperty('ders_id', ders['ders_id'])
            checkbox.stateChanged.connect(self.update_course_stats)
            row_layout.addWidget(checkbox, 1)
            
            # Duration label
            duration_label = QLabel("Süre:")
            duration_label.setStyleSheet("color: #6b7280; font-size: 11px;")
            row_layout.addWidget(duration_label)
            
            # Duration spinbox
            duration_spinbox = QSpinBox()
            duration_spinbox.setRange(1, 999)
            duration_spinbox.setValue(75)  # Default
            duration_spinbox.setSuffix(" dk")
            duration_spinbox.setFixedWidth(90)
            duration_spinbox.setFixedHeight(28)
            duration_spinbox.setToolTip("Bu ders için sınav süresi")
            row_layout.addWidget(duration_spinbox)
            
            self.ders_checkboxes[ders['ders_id']] = checkbox
            self.ders_duration_spinboxes[ders['ders_id']] = duration_spinbox
            self.ders_container_layout.addWidget(row_widget)
        
        self.update_course_stats()
    
    def filter_courses(self):
        """Filter courses based on search"""
        search_text = self.ders_search.text().lower()
        
        for ders_id, checkbox in self.ders_checkboxes.items():
            text = checkbox.text().lower()
            # Show/hide the parent row widget
            checkbox.parent().setVisible(search_text in text)
    
    def select_all_courses(self):
        """Select all courses"""
        for checkbox in self.ders_checkboxes.values():
            checkbox.setChecked(True)
        self.update_course_stats()
    
    def clear_all_courses(self):
        """Clear all course selections"""
        for checkbox in self.ders_checkboxes.values():
            checkbox.setChecked(False)
        self.update_course_stats()
    
    def toggle_all_courses(self):
        """Toggle all course selections"""
        all_checked = all(cb.isChecked() for cb in self.ders_checkboxes.values())
        
        for checkbox in self.ders_checkboxes.values():
            checkbox.setChecked(not all_checked)
        
        self.update_course_stats()
    
    def update_course_stats(self):
        """Update course selection statistics"""
        total = len(self.ders_checkboxes)
        selected = sum(1 for cb in self.ders_checkboxes.values() if cb.isChecked())
        self.ders_stats_label.setText(f"📊 Seçili: {selected} / {total} ders")
    
    def show_parallel_exams(self):
        """Show which courses can be held in parallel (no common students)"""
        try:
            # Get all courses
            dersler = self.ders_model.get_dersler_by_bolum(self.bolum_id)
            if not dersler or len(dersler) < 2:
                QMessageBox.information(self, "Bilgi", "En az 2 ders olmalıdır!")
                return
            
            # Build student-course mapping
            course_students = {}
            course_info = {}
            
            for ders in dersler:
                ogrenciler = self.ogrenci_model.get_ogrenciler_by_ders(ders['ders_id'])
                student_ids = set(o['ogrenci_no'] for o in ogrenciler)
                course_students[ders['ders_id']] = student_ids
                course_info[ders['ders_id']] = {
                    'ders_kodu': ders['ders_kodu'],
                    'ders_adi': ders['ders_adi'],
                    'sinif': ders.get('sinif', 0),
                    'ogrenci_sayisi': len(student_ids)
                }
            
            # Find ALL course pairs (no filtering)
            all_pairs = []
            
            course_ids = list(course_info.keys())
            
            # DEBUG: Log course count
            logger.info(f"🔍 Ortak Öğrenci Analizi:")
            logger.info(f"   Toplam ders sayısı: {len(course_ids)}")
            logger.info(f"   Beklenen çift sayısı: {len(course_ids) * (len(course_ids) - 1) // 2}")
            
            total_comparisons = 0
            # Check EVERY course against EVERY other course (no optimization)
            for ders_id1 in course_ids:
                for ders_id2 in course_ids:
                    # Skip comparing a course with itself
                    if ders_id1 == ders_id2:
                        continue
                    
                    # Skip duplicate pairs (A,B) same as (B,A)
                    if ders_id1 > ders_id2:
                        continue
                    
                    total_comparisons += 1
                    
                    shared = len(course_students[ders_id1] & course_students[ders_id2])
                    
                    # Add ALL pairs to the list (no filtering!)
                    all_pairs.append((
                        course_info[ders_id1]['ders_kodu'],
                        course_info[ders_id2]['ders_kodu'],
                        course_info[ders_id1]['sinif'],
                        course_info[ders_id2]['sinif'],
                        shared  # Ortak öğrenci sayısı
                    ))
            
            # DEBUG: Log results
            logger.info(f"   Yapılan karşılaştırma: {total_comparisons}")
            logger.info(f"   Toplam gösterilecek: {len(all_pairs)}")
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Tüm Ders Çiftleri - Ortak Öğrenci Analizi")
            dialog.setMinimumSize(1000, 700)
            
            layout = QVBoxLayout(dialog)
            
            # Header
            header = QLabel(f"📊 Tüm Ders Çiftleri Analizi ({len(all_pairs)} çift)")
            header.setFont(QFont("Segoe UI", 14, QFont.Bold))
            layout.addWidget(header)
            
            # Info with statistics
            zero_conflict = sum(1 for p in all_pairs if p[4] == 0)
            high_conflict = sum(1 for p in all_pairs if p[4] >= 10)
            
            info = QLabel(
                f"{len(course_ids)} ders × {len(course_ids)-1} ders ÷ 2 = {len(all_pairs)} benzersiz ders çifti\n\n"
                f"✅ Ortak öğrencisi olmayan: {zero_conflict} çift\n"
                f"⚠️ Orta çakışma (5-9 öğrenci): {sum(1 for p in all_pairs if 5 <= p[4] < 10)} çift\n"
                f"❌ Yüksek çakışma (10+ öğrenci): {high_conflict} çift"
            )
            info.setStyleSheet("color: #6b7280; padding: 10px; background: #f3f4f6; border-radius: 4px;")
            layout.addWidget(info)
            
            # Sort by shared students (descending)
            all_pairs.sort(key=lambda x: x[4], reverse=True)
            
            # Table with ALL pairs
            table = QTableWidget()
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels(["Ders 1", "Sınıf", "Ders 2", "Sınıf", "Ortak Öğrenci", "Durum"])
            table.setRowCount(len(all_pairs))
            
            for row, (d1, d2, s1, s2, shared) in enumerate(all_pairs):
                # Ders 1
                item1 = QTableWidgetItem(d1)
                item1.setFont(QFont("Segoe UI", 9))
                table.setItem(row, 0, item1)
                
                # Sınıf 1
                class1_item = QTableWidgetItem(f"{s1}. Sınıf")
                class1_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 1, class1_item)
                
                # Ders 2
                item2 = QTableWidgetItem(d2)
                item2.setFont(QFont("Segoe UI", 9))
                table.setItem(row, 2, item2)
                
                # Sınıf 2
                class2_item = QTableWidgetItem(f"{s2}. Sınıf")
                class2_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 3, class2_item)
                
                # Ortak öğrenci sayısı
                count_item = QTableWidgetItem(str(shared))
                count_item.setTextAlignment(Qt.AlignCenter)
                count_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                
                # Color code based on shared students
                if shared == 0:
                    count_item.setForeground(QColor("#10b981"))  # Green - can be parallel
                elif shared < 5:
                    count_item.setForeground(QColor("#3b82f6"))  # Blue - low conflict
                elif shared < 10:
                    count_item.setForeground(QColor("#f59e0b"))  # Orange - medium
                else:
                    count_item.setForeground(QColor("#dc2626"))  # Red - high conflict
                
                table.setItem(row, 4, count_item)
                
                # Durum
                if shared == 0:
                    status = "✅ Paralel yapılabilir"
                elif shared < 5:
                    status = "ℹ️ Az çakışma"
                elif shared < 10:
                    status = "⚠️ Orta çakışma"
                else:
                    status = "❌ Yüksek çakışma"
                
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 5, status_item)
            
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.setAlternatingRowColors(True)
            table.setSortingEnabled(True)  # Enable sorting
            layout.addWidget(table)
            
            # Close button
            close_btn = QPushButton("Kapat")
            close_btn.setFixedHeight(35)
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error analyzing parallel exams: {e}")
            QMessageBox.critical(self, "Hata", f"Analiz hatası: {str(e)}")
    
    def update_all_course_durations(self, value):
        """Update all course duration spinboxes when default duration changes"""
        for spinbox in self.ders_duration_spinboxes.values():
            spinbox.setValue(value)
    
    def create_schedule(self):
        """Create exam schedule"""
        # Validate dates
        if self.baslangic_tarih.dateTime() >= self.bitis_tarih.dateTime():
            QMessageBox.warning(self, "Uyarı", "Bitiş tarihi başlangıç tarihinden sonra olmalıdır!")
            return
        
        # Get allowed weekdays
        allowed_weekdays = [day for day, checkbox in self.gun_checkboxes.items() if checkbox.isChecked()]
        
        if not allowed_weekdays:
            QMessageBox.warning(self, "Uyarı", "En az bir gün seçmelisiniz!")
            return
        
        # Get selected courses
        selected_ders_ids = [ders_id for ders_id, checkbox in self.ders_checkboxes.items() if checkbox.isChecked()]
        
        if not selected_ders_ids:
            QMessageBox.warning(self, "Uyarı", "En az bir ders seçmelisiniz!")
            return
        
        # Get custom durations for each course
        ders_sureleri = {}
        for ders_id, spinbox in self.ders_duration_spinboxes.items():
            if ders_id in selected_ders_ids:
                ders_sureleri[ders_id] = spinbox.value()
        
        # Format time strings
        ilk_sinav = f"{self.ilk_sinav_saat.value():02d}:{self.ilk_sinav_dakika.value():02d}"
        son_sinav = f"{self.son_sinav_saat.value():02d}:{self.son_sinav_dakika.value():02d}"
        ogle_baslangic = f"{self.ogle_baslangic_saat.value():02d}:{self.ogle_baslangic_dakika.value():02d}"
        ogle_bitis = f"{self.ogle_bitis_saat.value():02d}:{self.ogle_bitis_dakika.value():02d}"
        
        params = {
            'bolum_id': self.bolum_id,
            'sinav_tipi': self.sinav_tipi_combo.currentText(),
            'baslangic_tarih': self.baslangic_tarih.dateTime().toPython(),
            'bitis_tarih': self.bitis_tarih.dateTime().toPython(),
            'varsayilan_sinav_suresi': self.sinav_suresi.value(),
            'ara_suresi': self.ara_suresi.value(),
            'allowed_weekdays': allowed_weekdays,
            'selected_ders_ids': selected_ders_ids,
            'gunluk_ilk_sinav': ilk_sinav,
            'gunluk_son_sinav': son_sinav,
            'ogle_arasi_baslangic': ogle_baslangic,
            'ogle_arasi_bitis': ogle_bitis,
            'no_parallel_exams': self.ayni_anda_sinav_checkbox.isChecked(),
            'class_per_day_limit': self.gunluk_sinav_limiti.value(),
            'ders_sinavlari_suresi': ders_sureleri,
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
        
        # Stop and cleanup thread
        if hasattr(self, 'planning_thread') and self.planning_thread:
            self.planning_thread.quit()
            self.planning_thread.wait()
            self.planning_thread = None
        
        schedule = result.get('schedule', [])
        
        if schedule and result.get('success'):
            # Show result dialog
            params = {
                'bolum_id': self.bolum_id,
                'sinav_tipi': self.sinav_tipi_combo.currentText()
            }
            dialog = ProgramResultDialog(schedule, params, self)
            dialog.exec()
            
            # Refresh programs list
            self.load_existing_programs()
        else:
            # Show error
            message = result.get('message', 'Program oluşturulamadı!')
            QMessageBox.warning(self, "Hata", message)
    
    def on_planning_error(self, error_msg):
        """Handle planning error"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.create_btn.setEnabled(True)
        
        # Stop and cleanup thread
        if hasattr(self, 'planning_thread') and self.planning_thread:
            self.planning_thread.quit()
            self.planning_thread.wait()
            self.planning_thread = None
        
        QMessageBox.critical(self, "Hata", f"Program oluşturulurken hata oluştu:\n{error_msg}")
