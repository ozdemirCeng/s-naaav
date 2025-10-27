"""
Ders Yükleme (Course Upload) View
Professional interface for uploading and managing courses from Excel
"""

import logging

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QFileDialog, QMessageBox, QGroupBox, QSplitter,
    QComboBox
)

from controllers.ders_controller import DersController
from models.database import db
from models.ders_model import DersModel
from models.ogrenci_model import OgrenciModel
from utils.excel_parser import ExcelParser

logger = logging.getLogger(__name__)


class ExcelLoadThread(QThread):
    """Thread for loading Excel file"""
    progress = Signal(int)
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        try:
            parser = ExcelParser()
            dersler = parser.parse_ders_listesi(self.file_path)
            self.finished.emit(dersler)
        except Exception as e:
            self.error.emit(str(e))


class DersYukleView(QWidget):
    """Course upload and management view"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id', 1)
        
        self.ders_model = DersModel(db)
        self.ogrenci_model = OgrenciModel(db)
        self.ders_controller = DersController(self.ders_model)
        
        self.pending_dersler = []
        
        self.setup_ui()
        self.load_existing_dersler()
    
    def setup_ui(self):
        """Setup UI - table first, info last"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Compact Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("📚 Ders Listesi")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        
        upload_btn = QPushButton("📤 Excel Yükle")
        upload_btn.setObjectName("primaryBtn")
        upload_btn.setFixedHeight(36)
        upload_btn.setCursor(Qt.PointingHandCursor)
        upload_btn.clicked.connect(self.upload_excel)
        
        export_btn = QPushButton("📊 Excel'e Aktar")
        export_btn.setFixedHeight(36)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self.export_to_excel)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(export_btn)
        header_layout.addWidget(upload_btn)
        
        layout.addWidget(header)
        
        # Filter section - sınıf seçimi
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(0, 8, 0, 8)
        
        filter_label = QLabel("🎓 Sınıf:")
        filter_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        
        self.class_filter = QComboBox()
        self.class_filter.addItems([
            "Tüm Dersler",
            "1. Sınıf",
            "2. Sınıf", 
            "3. Sınıf",
            "4. Sınıf",
            "Seçmeli Dersler"
        ])
        self.class_filter.setFixedHeight(32)
        self.class_filter.setMinimumWidth(200)
        self.class_filter.currentTextChanged.connect(self.filter_by_class)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.class_filter)
        filter_layout.addStretch()
        
        layout.addWidget(filter_frame)
        
        # Splitter for courses and students
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Courses table
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)  # Added column for Zorunlu/Seçmeli
        self.table.setHorizontalHeaderLabels([
            "DERS KODU", "DERSİN ADI", "DERSİ VEREN ÖĞR. ELEMANI", "SINIF", "TÜR"
        ])
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_course_students)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)     # DERS KODU
        header.setSectionResizeMode(1, QHeaderView.Stretch)   # DERSİN ADI
        header.setSectionResizeMode(2, QHeaderView.Stretch)   # ÖĞR. ELEMANI
        header.setSectionResizeMode(3, QHeaderView.Fixed)     # SINIF
        header.setSectionResizeMode(4, QHeaderView.Fixed)     # TÜR
        
        self.table.setColumnWidth(0, 100)  # DERS KODU
        self.table.setColumnWidth(3, 60)   # SINIF
        self.table.setColumnWidth(4, 90)   # TÜR
        
        left_layout.addWidget(self.table)
        
        # Course action buttons
        course_actions = QHBoxLayout()
        
        select_all_btn = QPushButton("☑️ Tümünü Seç")
        select_all_btn.setFixedHeight(32)
        select_all_btn.setCursor(Qt.PointingHandCursor)
        select_all_btn.clicked.connect(self.select_all_courses)
        
        deselect_all_btn = QPushButton("☐ Seçimi Kaldır")
        deselect_all_btn.setFixedHeight(32)
        deselect_all_btn.setCursor(Qt.PointingHandCursor)
        deselect_all_btn.clicked.connect(self.deselect_all_courses)
        
        edit_course_btn = QPushButton("✏️ Düzenle")
        edit_course_btn.setFixedHeight(32)
        edit_course_btn.setCursor(Qt.PointingHandCursor)
        edit_course_btn.clicked.connect(self.edit_selected_course)
        
        delete_course_btn = QPushButton("🗑️ Sil")
        delete_course_btn.setFixedHeight(32)
        delete_course_btn.setCursor(Qt.PointingHandCursor)
        delete_course_btn.setObjectName("dangerBtn")
        delete_course_btn.clicked.connect(self.delete_selected_courses)
        
        course_actions.addWidget(select_all_btn)
        course_actions.addWidget(deselect_all_btn)
        course_actions.addWidget(edit_course_btn)
        course_actions.addWidget(delete_course_btn)
        course_actions.addStretch()
        
        left_layout.addLayout(course_actions)
        splitter.addWidget(left_widget)
        
        # Right side - Students table
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        students_header = QLabel("👥 Dersi Alan Öğrenciler")
        students_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        students_header.setStyleSheet("padding: 8px; background-color: #f3f4f6; border-radius: 4px;")
        right_layout.addWidget(students_header)
        
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(3)
        self.students_table.setHorizontalHeaderLabels(["Öğrenci No", "Ad Soyad", "Sınıf"])
        self.students_table.verticalHeader().setVisible(False)
        self.students_table.setAlternatingRowColors(True)
        self.students_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        students_header_view = self.students_table.horizontalHeader()
        students_header_view.setSectionResizeMode(0, QHeaderView.Fixed)
        students_header_view.setSectionResizeMode(1, QHeaderView.Stretch)
        students_header_view.setSectionResizeMode(2, QHeaderView.Fixed)
        
        self.students_table.setColumnWidth(0, 100)
        self.students_table.setColumnWidth(2, 60)
        
        right_layout.addWidget(self.students_table)
        
        self.students_stats = QLabel("Bir ders seçin")
        self.students_stats.setStyleSheet("color: #6b7280; font-size: 11px; padding: 8px;")
        right_layout.addWidget(self.students_stats)
        
        splitter.addWidget(right_widget)
        
        # Set splitter proportions (60% courses, 40% students)
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        
        layout.addWidget(splitter, stretch=1)  # Give most space to table
        
        # Stats
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Segoe UI", 10))
        self.stats_label.setStyleSheet("color: #6b7280; padding: 6px;")
        layout.addWidget(self.stats_label)
        
        # Info card at bottom - compact
        info_card = QGroupBox("💡 Excel Format Bilgisi")
        info_card.setMaximumHeight(100)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 8, 12, 8)
        
        info_text = QLabel(
            "Excel: DERS KODU • DERSİN ADI • DERSİ VEREN ÖĞR. ELEMANI + Sınıf başlıkları (1. Sınıf, 2. Sınıf, vb.)"
        )
        info_text.setStyleSheet("color: #6b7280; font-size: 11px;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_card)
        
        # Store all courses
        self.all_courses = []
    
    def filter_by_class(self, filter_text):
        """Filter courses by class - Excel başlıklarından alınan sınıf bilgisi ile"""
        if not self.all_courses:
            return
        
        filtered_courses = []
        
        if filter_text == "Tüm Dersler":
            filtered_courses = self.all_courses
        elif filter_text == "1. Sınıf":
            filtered_courses = [d for d in self.all_courses if d.get('sinif', 0) == 1]
        elif filter_text == "2. Sınıf":
            filtered_courses = [d for d in self.all_courses if d.get('sinif', 0) == 2]
        elif filter_text == "3. Sınıf":
            filtered_courses = [d for d in self.all_courses if d.get('sinif', 0) == 3]
        elif filter_text == "4. Sınıf":
            filtered_courses = [d for d in self.all_courses if d.get('sinif', 0) == 4]
        elif filter_text == "Seçmeli Dersler":
            filtered_courses = [d for d in self.all_courses if d.get('ders_yapisi', '') == 'Seçmeli']
        
        self.populate_table(filtered_courses, existing=True)
    
    def load_existing_dersler(self):
        """Load existing courses"""
        try:
            dersler = self.ders_model.get_dersler_by_bolum(self.bolum_id)
            self.populate_table(dersler, existing=True)
            self.update_stats(len(dersler), 0)
        except Exception as e:
            logger.error(f"Error loading courses: {e}")
            QMessageBox.critical(self, "Hata", f"Dersler yüklenirken hata oluştu:\n{str(e)}")
    
    def populate_table(self, dersler, existing=False):
        """Populate table with course data"""
        self.table.setRowCount(0)
        
        # Store for filtering
        if not hasattr(self, 'all_courses') or not existing:
            self.all_courses = dersler
        
        for row, ders in enumerate(dersler):
            self.table.insertRow(row)
            
            # DERS KODU
            kod_item = QTableWidgetItem(str(ders.get('ders_kodu', '')))
            self.table.setItem(row, 0, kod_item)
            
            # DERSİN ADI
            adi_item = QTableWidgetItem(str(ders.get('ders_adi', '')))
            self.table.setItem(row, 1, adi_item)
            
            # DERSİ VEREN ÖĞR. ELEMANI
            ogretim_elemani = str(ders.get('ogretim_elemani', '-'))
            elem_item = QTableWidgetItem(ogretim_elemani)
            self.table.setItem(row, 2, elem_item)
            
            # SINIF
            sinif = ders.get('sinif', 0)
            sinif_text = f"{sinif}. Sınıf" if sinif > 0 else "-"
            sinif_item = QTableWidgetItem(sinif_text)
            sinif_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, sinif_item)
            
            # TÜR (Zorunlu/Seçmeli)
            ders_yapisi = ders.get('ders_yapisi', 'Zorunlu')
            tur_item = QTableWidgetItem(ders_yapisi)
            tur_item.setTextAlignment(Qt.AlignCenter)
            
            # Color code based on type
            if ders_yapisi == 'Seçmeli':
                tur_item.setForeground(QColor('#f59e0b'))  # Orange for elective
                tur_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            else:
                tur_item.setForeground(QColor('#059669'))  # Green for mandatory
            
            self.table.setItem(row, 4, tur_item)
    
    def upload_excel(self):
        """Upload Excel file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Excel Dosyası Seç",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            self.load_excel(file_path)
    
    def load_excel(self, file_path):
        """Load Excel file in background thread"""
        self.thread = ExcelLoadThread(file_path)
        self.thread.finished.connect(self.on_excel_loaded)
        self.thread.error.connect(self.on_excel_error)
        self.thread.start()
    
    def on_excel_loaded(self, dersler):
        """Handle loaded Excel data with validation summary"""
        if not dersler:
            QMessageBox.warning(self, "Uyarı", "Excel dosyasında ders bulunamadı!")
            return
        
        self.pending_dersler = dersler
        self.populate_table(dersler, existing=False)
        self.update_stats(0, len(dersler))
        
        # Show summary with validation info
        summary_msg = f"✅ {len(dersler)} ders başarıyla yüklendi"
        
        # Check for any validation warnings in logs
        # (errors are already shown in on_excel_error)
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Dersleri Kaydet",
            f"{summary_msg}\n\nVeritabanına kaydetmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.save_dersler()
    
    def on_excel_error(self, error_msg):
        """Handle Excel loading error with detailed information"""
        # Create detailed error dialog
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle("❌ Excel Yükleme Hatası")
        
        # Parse error message to provide better formatting
        if "❌" in error_msg:
            # Formatted error from parser (e.g., format errors, missing columns)
            error_dialog.setText("Excel formatı hatalı")
            error_dialog.setInformativeText(error_msg)
        elif "Satır" in error_msg and error_msg.count("Satır") > 3:
            # Multiple row errors - show summary
            lines = [line for line in error_msg.split('\n') if line.strip()]
            row_count = error_msg.count("Satır")
            
            error_dialog.setText(f"Excel'de {row_count} satırda hata bulundu")
            error_dialog.setInformativeText(
                "Lütfen Excel dosyasını kontrol edin ve düzeltip tekrar yükleyin.\n\n"
                "Detaylar için 'Show Details' butonuna tıklayın."
            )
            # Format detailed text for better readability
            detailed_text = error_msg.replace("Satır ", "\n• Satır ")
            error_dialog.setDetailedText(detailed_text)
        else:
            # Generic or single error
            error_dialog.setText("Excel dosyası yüklenirken hata oluştu")
            error_dialog.setInformativeText(error_msg)
        
        error_dialog.setStandardButtons(QMessageBox.Ok)
        error_dialog.exec()
    
    def save_dersler(self):
        """Save courses to database with detailed error reporting"""
        if not self.pending_dersler:
            return
        
        try:
            success_count = 0
            error_count = 0
            error_details = []
            
            for idx, ders in enumerate(self.pending_dersler, 1):
                excel_row = idx + 1  # Account for header row
                ders['bolum_id'] = self.bolum_id
                result = self.ders_controller.create_ders(ders)
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    # Track which row failed
                    error_msg = f"Satır {excel_row} ({ders.get('ders_kodu', '?')} - {ders.get('ders_adi', '?')}): {result['message']}"
                    error_details.append(error_msg)
                    logger.warning(error_msg)
            
            # Show detailed results
            if error_count > 0:
                error_dialog = QMessageBox(self)
                error_dialog.setIcon(QMessageBox.Warning)
                error_dialog.setWindowTitle("Kaydetme Sonuçları")
                error_dialog.setText(
                    f"✅ {success_count} ders kaydedildi\n"
                    f"❌ {error_count} ders kaydedilemedi"
                )
                
                # Show first 20 errors in detail
                detailed_text = "\n".join(error_details[:20])
                if len(error_details) > 20:
                    detailed_text += f"\n\n... ve {len(error_details) - 20} hata daha"
                
                error_dialog.setDetailedText(detailed_text)
                error_dialog.setStandardButtons(QMessageBox.Ok)
                error_dialog.exec()
            else:
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"✅ {success_count} ders başarıyla kaydedildi!"
                )
            
            self.pending_dersler = []
            self.load_existing_dersler()
            
        except Exception as e:
            logger.error(f"Error saving courses: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Dersler kaydedilirken hata oluştu:\n{str(e)}")
    
    def update_stats(self, existing, pending):
        """Update statistics label"""
        self.stats_label.setText(
            f"📊 Kayıtlı: {existing} | Beklemede: {pending}"
        )
    
    def show_course_students(self):
        """Show students of selected course"""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            self.students_table.setRowCount(0)
            self.students_stats.setText("Bir ders seçin")
            return
        
        row = selected_rows[0].row()
        ders_kodu = self.table.item(row, 0).text()
        ders_adi = self.table.item(row, 1).text()
        
        # Get ders_id from model
        try:
            ders = self.ders_model.get_ders_by_kod(self.bolum_id, ders_kodu)
            if not ders:
                self.students_table.setRowCount(0)
                self.students_stats.setText("❌ Ders bulunamadı")
                return
            
            # Get students taking this course
            ogrenciler = self.ogrenci_model.get_ogrenciler_by_ders(ders['ders_id'])
            
            # Update students table
            self.students_table.setRowCount(0)
            
            if not ogrenciler:
                self.students_stats.setText(f"📚 {ders_kodu} - Kayıtlı öğrenci yok")
            else:
                for row_idx, ogrenci in enumerate(ogrenciler):
                    self.students_table.insertRow(row_idx)
                    
                    no_item = QTableWidgetItem(ogrenci.get('ogrenci_no', ''))
                    ad_item = QTableWidgetItem(ogrenci.get('ad_soyad', ''))
                    sinif_item = QTableWidgetItem(str(ogrenci.get('sinif', '')))
                    sinif_item.setTextAlignment(Qt.AlignCenter)
                    
                    self.students_table.setItem(row_idx, 0, no_item)
                    self.students_table.setItem(row_idx, 1, ad_item)
                    self.students_table.setItem(row_idx, 2, sinif_item)
                
                self.students_stats.setText(f"📚 {ders_kodu} - {len(ogrenciler)} öğrenci")
            
        except Exception as e:
            logger.error(f"Error loading course students: {e}")
            self.students_stats.setText(f"❌ Hata: {str(e)}")
    
    def edit_selected_course(self):
        """Edit selected course"""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir ders seçin!")
            return
        
        row = selected_rows[0].row()
        durum = self.table.item(row, 5).text()
        
        if durum == "Beklemede":
            QMessageBox.warning(self, "Uyarı", "Beklemedeki dersler düzenlenemez! Önce kaydedin.")
            return
        
        ders_kodu = self.table.item(row, 0).text()
        ders_adi = self.table.item(row, 1).text()
        kredi = self.table.item(row, 2).text()
        yariyil = self.table.item(row, 3).text()
        ders_yapisi = self.table.item(row, 4).text()
        
        # Create edit dialog
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QSpinBox, QComboBox, QFormLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Ders Düzenle")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        
        kod_edit = QLineEdit(ders_kodu)
        kod_edit.setReadOnly(True)
        ad_edit = QLineEdit(ders_adi)
        kredi_edit = QSpinBox()
        kredi_edit.setRange(1, 10)
        kredi_edit.setValue(int(kredi) if kredi else 3)
        yariyil_edit = QSpinBox()
        yariyil_edit.setRange(1, 8)
        yariyil_edit.setValue(int(yariyil) if yariyil else 1)
        yapi_combo = QComboBox()
        yapi_combo.addItems(["Zorunlu", "Seçmeli"])
        yapi_combo.setCurrentText(ders_yapisi)
        
        form.addRow("Ders Kodu:", kod_edit)
        form.addRow("Ders Adı:", ad_edit)
        form.addRow("Kredi:", kredi_edit)
        form.addRow("Yarıyıl:", yariyil_edit)
        form.addRow("Ders Yapısı:", yapi_combo)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            # Update course
            ders = self.ders_model.get_ders_by_kod(self.bolum_id, ders_kodu)
            if not ders:
                QMessageBox.warning(self, "Hata", "Ders bulunamadı!")
                return
            
            updated_data = {
                'ders_adi': ad_edit.text().strip(),
                'kredi': kredi_edit.value(),
                'yariyil': yariyil_edit.value(),
                'ders_yapisi': yapi_combo.currentText()
            }
            
            result = self.ders_controller.update_ders(ders['ders_id'], updated_data)
            
            if result['success']:
                QMessageBox.information(self, "Başarılı", result['message'])
                self.load_existing_dersler()
            else:
                QMessageBox.critical(self, "Hata", result['message'])
    
    def select_all_courses(self):
        """Select all courses in table"""
        self.table.selectAll()
    
    def deselect_all_courses(self):
        """Deselect all courses"""
        self.table.clearSelection()
    
    def delete_selected_courses(self):
        """Delete multiple selected courses"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen silmek için en az bir ders seçin!")
            return
        
        # Get course list from selected rows
        course_list = []
        for index in selected_rows:
            row = index.row()
            ders_kodu = self.table.item(row, 0).text() if self.table.item(row, 0) else None
            ders_adi = self.table.item(row, 1).text() if self.table.item(row, 1) else "İsimsiz"
            if ders_kodu:
                course_list.append((ders_kodu, ders_adi))
        
        if not course_list:
            QMessageBox.warning(self, "Uyarı", "Silinecek ders bulunamadı!")
            return
        
        reply = QMessageBox.question(
            self,
            "Dersleri Sil",
            f"{len(course_list)} dersi silmek istediğinizden emin misiniz?\n\n"
            "Bu işlem geri alınamaz!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success_count = 0
            error_count = 0
            
            for ders_kodu, ders_adi in course_list:
                ders = self.ders_model.get_ders_by_kod(self.bolum_id, ders_kodu)
                if ders:
                    result = self.ders_controller.delete_ders(ders['ders_id'])
                    if result['success']:
                        success_count += 1
                    else:
                        error_count += 1
                        logger.error(f"Failed to delete {ders_kodu}: {result['message']}")
                else:
                    error_count += 1
            
            QMessageBox.information(
                self,
                "İşlem Tamamlandı",
                f"✅ {success_count} ders silindi\n❌ {error_count} ders silinemedi"
            )
            
            self.load_existing_dersler()
    
    def delete_selected_course(self):
        """Delete selected course"""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen silmek için bir ders seçin!")
            return
        
        row = selected_rows[0].row()
        ders_kodu = self.table.item(row, 0).text() if self.table.item(row, 0) else None
        ders_adi = self.table.item(row, 1).text() if self.table.item(row, 1) else "İsimsiz"
        
        if not ders_kodu:
            QMessageBox.warning(self, "Uyarı", "Ders kodu bulunamadı!")
            return
        
        ders = self.ders_model.get_ders_by_kod(self.bolum_id, ders_kodu)
        if not ders:
            QMessageBox.warning(self, "Hata", "Ders bulunamadı!")
            return
        
        reply = QMessageBox.question(
            self,
            "Ders Sil",
            f"'{ders_adi}' ({ders_kodu}) dersini silmek istediğinizden emin misiniz?\n\n"
            "Bu işlem geri alınamaz!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            result = self.ders_controller.delete_ders(ders['ders_id'])
            
            if result['success']:
                QMessageBox.information(self, "Başarılı", result['message'])
                self.load_existing_dersler()
            else:
                QMessageBox.critical(self, "Hata", result['message'])
    
    def export_to_excel(self):
        """Export courses to Excel"""
        try:
            import pandas as pd
            from datetime import datetime
            
            # Get all courses
            dersler = self.ders_model.get_dersler_by_bolum(self.bolum_id)
            
            if not dersler:
                QMessageBox.warning(self, "Uyarı", "Aktarılacak ders bulunamadı!")
                return
            
            # Ask for save location
            default_name = f"ders_listesi_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Excel Dosyası Kaydet",
                default_name,
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # Create DataFrame
            data = []
            for ders in dersler:
                data.append({
                    'Ders Kodu': ders['ders_kodu'],
                    'Ders Adı': ders['ders_adi'],
                    'Kredi': ders.get('kredi', ''),
                    'Yarıyıl': ders.get('yariyil', ''),
                    'Ders Yapısı': ders.get('ders_yapisi', '')
                })
            
            df = pd.DataFrame(data)
            
            # Write to Excel with formatting
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Dersler')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Dersler']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = max_length
            
            QMessageBox.information(
                self,
                "Başarılı",
                f"Ders listesi başarıyla aktarıldı!\n{len(data)} ders\n\n{file_path}"
            )
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            QMessageBox.critical(self, "Hata", f"Excel aktarma hatası:\n{str(e)}")
