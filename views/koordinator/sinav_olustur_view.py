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
    QTableWidgetItem, QHeaderView, QProgressBar, QCheckBox,
    QLineEdit, QScrollArea, QFileDialog
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
        
        self.sinav_suresi = QSpinBox()
        self.sinav_suresi.setMinimum(60)
        self.sinav_suresi.setMaximum(240)
        self.sinav_suresi.setValue(75)
        self.sinav_suresi.setSuffix(" dakika")
        params_layout.addRow("Sınav Süresi:", self.sinav_suresi)
        
        self.ara_suresi = QSpinBox()
        self.ara_suresi.setMinimum(0)
        self.ara_suresi.setMaximum(120)
        self.ara_suresi.setValue(15)
        self.ara_suresi.setSuffix(" dakika")
        params_layout.addRow("Bekleme Süresi:", self.ara_suresi)
        
        layout.addWidget(params_card)
        
        # Weekday selection
        gunler_card = QGroupBox("Program Dahil Olacak Günler")
        gunler_layout = QVBoxLayout(gunler_card)
        
        gunler_grid = QHBoxLayout()
        self.gun_checkboxes = {}
        gun_isimleri = {
            0: "Pazartesi",
            1: "Salı",
            2: "Çarşamba",
            3: "Perşembe",
            4: "Cuma",
            5: "Cumartesi",
            6: "Pazar"
        }
        
        for day_num, day_name in gun_isimleri.items():
            checkbox = QCheckBox(day_name)
            # Weekdays checked by default
            if day_num < 5:
                checkbox.setChecked(True)
            self.gun_checkboxes[day_num] = checkbox
            gunler_grid.addWidget(checkbox)
        
        gunler_layout.addLayout(gunler_grid)
        layout.addWidget(gunler_card)
        
        # Course selection
        ders_card = QGroupBox("Programa Dahil Olacak Dersler")
        ders_layout = QVBoxLayout(ders_card)
        
        # Search and select all
        ders_toolbar = QHBoxLayout()
        self.ders_search = QLineEdit()
        self.ders_search.setPlaceholderText("Ders ara...")
        self.ders_search.textChanged.connect(self.filter_courses)
        
        select_all_btn = QPushButton("Tümünü Seç/Kaldır")
        select_all_btn.clicked.connect(self.toggle_all_courses)
        select_all_btn.setFixedWidth(150)
        
        ders_toolbar.addWidget(self.ders_search)
        ders_toolbar.addWidget(select_all_btn)
        ders_layout.addLayout(ders_toolbar)
        
        # Scrollable course list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(250)
        
        self.ders_container = QWidget()
        self.ders_container_layout = QVBoxLayout(self.ders_container)
        self.ders_container_layout.setSpacing(4)
        self.ders_checkboxes = {}
        
        scroll.setWidget(self.ders_container)
        ders_layout.addWidget(scroll)
        
        # Stats
        self.ders_stats_label = QLabel("Yükleniyor...")
        self.ders_stats_label.setStyleSheet("color: #6b7280; font-size: 11px; padding: 4px;")
        ders_layout.addWidget(self.ders_stats_label)
        
        layout.addWidget(ders_card)
        
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
        
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Programı Kaydet")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.save_schedule)
        
        export_btn = QPushButton("📊 Excel'e Aktar")
        export_btn.setObjectName("secondaryBtn")
        export_btn.setFixedHeight(40)
        export_btn.clicked.connect(self.export_to_excel)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(export_btn)
        
        results_layout.addLayout(btn_layout)
        
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
                return
            
            if not derslikler:
                QMessageBox.warning(self, "Uyarı", "Henüz derslik tanımlanmamış!")
                return
            
            # Populate course checkboxes
            self.populate_course_list(dersler)
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def populate_course_list(self, dersler):
        """Populate course selection checkboxes"""
        # Clear existing
        while self.ders_container_layout.count():
            item = self.ders_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.ders_checkboxes.clear()
        
        for ders in dersler:
            checkbox = QCheckBox(f"{ders['ders_kodu']} - {ders['ders_adi']}")
            checkbox.setChecked(True)  # All selected by default
            checkbox.setProperty('ders_id', ders['ders_id'])
            checkbox.setProperty('ders_kodu', ders['ders_kodu'])
            checkbox.stateChanged.connect(self.update_course_stats)
            self.ders_checkboxes[ders['ders_id']] = checkbox
            self.ders_container_layout.addWidget(checkbox)
        
        self.update_course_stats()
    
    def filter_courses(self):
        """Filter courses based on search"""
        search_text = self.ders_search.text().lower()
        
        for ders_id, checkbox in self.ders_checkboxes.items():
            text = checkbox.text().lower()
            checkbox.setVisible(search_text in text)
    
    def toggle_all_courses(self):
        """Toggle all course selections"""
        # Check if all are selected
        all_checked = all(cb.isChecked() for cb in self.ders_checkboxes.values())
        
        # Toggle
        for checkbox in self.ders_checkboxes.values():
            checkbox.setChecked(not all_checked)
        
        self.update_course_stats()
    
    def update_course_stats(self):
        """Update course selection statistics"""
        total = len(self.ders_checkboxes)
        selected = sum(1 for cb in self.ders_checkboxes.values() if cb.isChecked())
        self.ders_stats_label.setText(f"Seçili: {selected} / {total} ders")
    
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
        
        params = {
            'bolum_id': self.bolum_id,
            'sinav_tipi': self.sinav_tipi_combo.currentText(),
            'baslangic_tarih': self.baslangic_tarih.dateTime().toPython(),
            'bitis_tarih': self.bitis_tarih.dateTime().toPython(),
            'sinav_suresi': self.sinav_suresi.value(),
            'ara_suresi': self.ara_suresi.value(),
            'allowed_weekdays': allowed_weekdays,
            'selected_ders_ids': selected_ders_ids
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
        
        schedule = result.get('schedule', [])
        
        if schedule:
            # Show partial or complete schedule
            self.current_schedule = schedule
            self.display_schedule(schedule)
        
        if result.get('success'):
            QMessageBox.information(
                self,
                "Başarılı",
                f"✅ Sınav programı başarıyla oluşturuldu!\n\n"
                f"Toplam {len(schedule)} sınav planlandı."
            )
        else:
            # Show warning with details and partial schedule
            unassigned = result.get('unassigned_courses', [])
            message = result.get('message', 'Program oluşturulamadı!')
            
            if schedule:
                message += f"\n\n✅ {len(schedule)} sınav yerleştirildi."
                message += f"\n❌ {len(unassigned)} ders yerleştirilemedi."
            
            QMessageBox.warning(self, "Kısmi Program Oluşturuldu", message)
    
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
    
    def export_to_excel(self):
        """Export schedule to Excel file"""
        if not hasattr(self, 'current_schedule') or not self.current_schedule:
            QMessageBox.warning(self, "Uyarı", "Aktarılacak program bulunamadı!")
            return
        
        import pandas as pd
        
        # Ask for save location
        default_name = f"sinav_programi_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel Dosyası Kaydet",
            default_name,
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            # Prepare data
            data = []
            for sinav in self.current_schedule:
                tarih = datetime.fromisoformat(sinav['tarih_saat']) if isinstance(sinav['tarih_saat'], str) else sinav['tarih_saat']
                
                data.append({
                    'Tarih': tarih.strftime('%d.%m.%Y'),
                    'Saat': tarih.strftime('%H:%M'),
                    'Gün': ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'][tarih.weekday()],
                    'Ders Kodu': sinav.get('ders_kodu', ''),
                    'Ders Adı': sinav.get('ders_adi', ''),
                    'Derslik': sinav.get('derslik_kodu', ''),
                    'Öğrenci Sayısı': sinav.get('ogrenci_sayisi', 0),
                    'Sınav Türü': sinav.get('sinav_tipi', ''),
                    'Süre (dk)': sinav.get('sure', 0)
                })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Create Excel writer
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Sınav Programı', index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Sınav Programı']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Style header row
                from openpyxl.styles import Font, PatternFill, Alignment
                header_fill = PatternFill(start_color="10b981", end_color="10b981", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                
                for cell in worksheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center')
            
            QMessageBox.information(
                self,
                "Başarılı",
                f"✅ Sınav programı Excel'e aktarıldı!\n\n{len(data)} sınav kaydedildi.\n\nDosya: {file_path}"
            )
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            QMessageBox.critical(self, "Hata", f"Excel'e aktarırken hata oluştu:\n{str(e)}")
