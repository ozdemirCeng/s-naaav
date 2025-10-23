"""
Öğrenci Yükleme (Student Upload) View
Professional interface for uploading and managing students from Excel
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QFileDialog, QMessageBox, QGroupBox, QLineEdit, QSplitter,
    QSpinBox, QFormLayout, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from models.database import db
from models.ogrenci_model import OgrenciModel
from controllers.ogrenci_controller import OgrenciController
from utils.excel_parser import ExcelParser

logger = logging.getLogger(__name__)


class OgrenciLoadThread(QThread):
    """Thread for loading student Excel file"""
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        try:
            parser = ExcelParser()
            ogrenciler = parser.parse_ogrenci_listesi(self.file_path)
            self.finished.emit(ogrenciler)
        except Exception as e:
            self.error.emit(str(e))


class OgrenciYukleView(QWidget):
    """Student upload and management view"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id', 1)
        
        self.ogrenci_model = OgrenciModel(db)
        self.ogrenci_controller = OgrenciController(self.ogrenci_model)
        
        self.pending_ogrenciler = []
        
        self.setup_ui()
        self.load_existing_ogrenciler()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Öğrenci Listesi Yönetimi 👥")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        
        upload_btn = QPushButton("📤 Excel Yükle")
        upload_btn.setObjectName("primaryBtn")
        upload_btn.setFixedHeight(40)
        upload_btn.setCursor(Qt.PointingHandCursor)
        upload_btn.clicked.connect(self.upload_excel)
        
        export_btn = QPushButton("📊 Excel'e Aktar")
        export_btn.setFixedHeight(40)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self.export_to_excel)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(export_btn)
        header_layout.addWidget(upload_btn)
        
        layout.addWidget(header)
        
        # Info card
        info_card = QGroupBox("ℹ️ Excel Formatı")
        info_layout = QVBoxLayout(info_card)
        
        info_text = QLabel(
            "Excel dosyası şu sütunları içermelidir:\n"
            "• Öğrenci No (örn: 210101001)\n"
            "• Ad Soyad (örn: Ahmet Yılmaz)\n"
            "• Sınıf (örn: 2)\n"
            "• E-posta (opsiyonel)"
        )
        info_text.setStyleSheet("color: #6b7280; font-size: 12px;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_card)
        
        # Search
        search_container = QFrame()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(16, 12, 16, 12)
        
        search_label = QLabel("🔍 Ara:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Öğrenci no veya ad ile ara...")
        self.search_input.textChanged.connect(self.filter_table)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        
        layout.addWidget(search_container)
        
        # Splitter for students and courses
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Students table
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Öğrenci No", "Ad Soyad", "Sınıf", "E-posta", "Durum"
        ])
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_student_courses)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(4, 100)
        
        left_layout.addWidget(self.table)
        
        # Student action buttons
        student_actions = QHBoxLayout()
        
        select_all_btn = QPushButton("☑️ Tümünü Seç")
        select_all_btn.setFixedHeight(32)
        select_all_btn.setCursor(Qt.PointingHandCursor)
        select_all_btn.clicked.connect(self.select_all_students)
        
        deselect_all_btn = QPushButton("☐ Seçimi Kaldır")
        deselect_all_btn.setFixedHeight(32)
        deselect_all_btn.setCursor(Qt.PointingHandCursor)
        deselect_all_btn.clicked.connect(self.deselect_all_students)
        
        edit_student_btn = QPushButton("✏️ Düzenle")
        edit_student_btn.setFixedHeight(32)
        edit_student_btn.setCursor(Qt.PointingHandCursor)
        edit_student_btn.clicked.connect(self.edit_selected_student)
        
        delete_student_btn = QPushButton("🗑️ Sil")
        delete_student_btn.setFixedHeight(32)
        delete_student_btn.setCursor(Qt.PointingHandCursor)
        delete_student_btn.setObjectName("dangerBtn")
        delete_student_btn.clicked.connect(self.delete_selected_students)
        
        student_actions.addWidget(select_all_btn)
        student_actions.addWidget(deselect_all_btn)
        student_actions.addWidget(edit_student_btn)
        student_actions.addWidget(delete_student_btn)
        student_actions.addStretch()
        
        left_layout.addLayout(student_actions)
        splitter.addWidget(left_widget)
        
        # Right side - Courses table
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        courses_header = QLabel("📚 Öğrencinin Aldığı Dersler")
        courses_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        courses_header.setStyleSheet("padding: 8px; background-color: #f3f4f6; border-radius: 4px;")
        right_layout.addWidget(courses_header)
        
        self.courses_table = QTableWidget()
        self.courses_table.setColumnCount(3)
        self.courses_table.setHorizontalHeaderLabels(["Ders Kodu", "Ders Adı", "Sınıf"])
        self.courses_table.verticalHeader().setVisible(False)
        self.courses_table.setAlternatingRowColors(True)
        self.courses_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        courses_header_view = self.courses_table.horizontalHeader()
        courses_header_view.setSectionResizeMode(0, QHeaderView.Fixed)
        courses_header_view.setSectionResizeMode(1, QHeaderView.Stretch)
        courses_header_view.setSectionResizeMode(2, QHeaderView.Fixed)
        
        self.courses_table.setColumnWidth(0, 100)
        self.courses_table.setColumnWidth(2, 60)
        
        right_layout.addWidget(self.courses_table)
        
        self.courses_stats = QLabel("Bir öğrenci seçin")
        self.courses_stats.setStyleSheet("color: #6b7280; font-size: 11px; padding: 8px;")
        right_layout.addWidget(self.courses_stats)
        
        splitter.addWidget(right_widget)
        
        # Set splitter proportions (60% students, 40% courses)
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        
        layout.addWidget(splitter)
        
        # Stats
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Segoe UI", 10))
        self.stats_label.setStyleSheet("color: #6b7280; padding: 8px;")
        layout.addWidget(self.stats_label)
    
    def load_existing_ogrenciler(self):
        """Load existing students"""
        try:
            ogrenciler = self.ogrenci_model.get_ogrenciler_by_bolum(self.bolum_id)
            self.populate_table(ogrenciler, existing=True)
            self.update_stats(len(ogrenciler), 0)
        except Exception as e:
            logger.error(f"Error loading students: {e}")
            QMessageBox.critical(self, "Hata", f"Öğrenciler yüklenirken hata oluştu:\n{str(e)}")
    
    def populate_table(self, ogrenciler, existing=False):
        """Populate table with student data"""
        self.table.setRowCount(0)
        
        for row, ogrenci in enumerate(ogrenciler):
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(ogrenci.get('ogrenci_no', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(str(ogrenci.get('ad_soyad', ''))))
            
            sinif_item = QTableWidgetItem(str(ogrenci.get('sinif', '')))
            sinif_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, sinif_item)
            
            self.table.setItem(row, 3, QTableWidgetItem(str(ogrenci.get('email', '-'))))
            
            durum = "✅ Kayıtlı" if existing else "⏳ Beklemede"
            durum_item = QTableWidgetItem(durum)
            durum_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, durum_item)
    
    def filter_table(self):
        """Filter table based on search"""
        search_text = self.search_input.text().lower()
        
        for row in range(self.table.rowCount()):
            no = self.table.item(row, 0).text().lower()
            ad = self.table.item(row, 1).text().lower()
            
            if search_text in no or search_text in ad:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)
    
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
        self.thread = OgrenciLoadThread(file_path)
        self.thread.finished.connect(self.on_excel_loaded)
        self.thread.error.connect(self.on_excel_error)
        self.thread.start()
    
    def on_excel_loaded(self, ogrenciler):
        """Handle loaded Excel data"""
        if not ogrenciler:
            QMessageBox.warning(self, "Uyarı", "Excel dosyasında öğrenci bulunamadı!")
            return
        
        self.pending_ogrenciler = ogrenciler
        self.populate_table(ogrenciler, existing=False)
        self.update_stats(0, len(ogrenciler))
        
        reply = QMessageBox.question(
            self,
            "Öğrencileri Kaydet",
            f"{len(ogrenciler)} öğrenci yüklendi. Veritabanına kaydetmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.save_ogrenciler()
    
    def on_excel_error(self, error_msg):
        """Handle Excel loading error"""
        QMessageBox.critical(self, "Hata", f"Excel dosyası yüklenirken hata oluştu:\n{error_msg}")
    
    def save_ogrenciler(self):
        """Save students to database"""
        if not self.pending_ogrenciler:
            return
        
        try:
            success_count = 0
            error_count = 0
            
            for ogrenci in self.pending_ogrenciler:
                ogrenci['bolum_id'] = self.bolum_id
                result = self.ogrenci_controller.create_ogrenci(ogrenci)
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    logger.warning(f"Failed to save student: {ogrenci['ogrenci_no']} - {result['message']}")
            
            QMessageBox.information(
                self,
                "İşlem Tamamlandı",
                f"✅ {success_count} öğrenci kaydedildi\n❌ {error_count} öğrenci kaydedilemedi"
            )
            
            self.pending_ogrenciler = []
            self.load_existing_ogrenciler()
            
        except Exception as e:
            logger.error(f"Error saving students: {e}")
            QMessageBox.critical(self, "Hata", f"Öğrenciler kaydedilirken hata oluştu:\n{str(e)}")
    
    def update_stats(self, existing, pending):
        """Update statistics label"""
        self.stats_label.setText(
            f"📊 Kayıtlı: {existing} | Beklemede: {pending}"
        )
    
    def show_student_courses(self):
        """Show courses of selected student"""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            self.courses_table.setRowCount(0)
            self.courses_stats.setText("Bir öğrenci seçin")
            return
        
        row = selected_rows[0].row()
        ogrenci_no = self.table.item(row, 0).text()
        ad_soyad = self.table.item(row, 1).text()
        
        # Get student's courses
        try:
            dersler = self.ogrenci_model.get_dersler_by_ogrenci(ogrenci_no)
            
            # Update courses table
            self.courses_table.setRowCount(0)
            
            if not dersler:
                self.courses_stats.setText(f"👤 {ad_soyad} - Kayıtlı ders yok")
            else:
                for row_idx, ders in enumerate(dersler):
                    self.courses_table.insertRow(row_idx)
                    
                    kod_item = QTableWidgetItem(ders.get('ders_kodu', ''))
                    ad_item = QTableWidgetItem(ders.get('ders_adi', ''))
                    sinif_item = QTableWidgetItem(str(ders.get('sinif', '')))
                    sinif_item.setTextAlignment(Qt.AlignCenter)
                    
                    self.courses_table.setItem(row_idx, 0, kod_item)
                    self.courses_table.setItem(row_idx, 1, ad_item)
                    self.courses_table.setItem(row_idx, 2, sinif_item)
                
                self.courses_stats.setText(f"👤 {ad_soyad} - {len(dersler)} ders")
            
        except Exception as e:
            logger.error(f"Error loading student courses: {e}")
            self.courses_stats.setText(f"❌ Hata: {str(e)}")
    
    def edit_selected_student(self):
        """Edit selected student"""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir öğrenci seçin!")
            return
        
        row = selected_rows[0].row()
        durum = self.table.item(row, 4).text()
        
        if durum == "Beklemede":
            QMessageBox.warning(self, "Uyarı", "Beklemedeki öğrenciler düzenlenemez! Önce kaydedin.")
            return
        
        ogrenci_no = self.table.item(row, 0).text()
        ad_soyad = self.table.item(row, 1).text()
        sinif = self.table.item(row, 2).text()
        email = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
        
        # Create edit dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Öğrenci Düzenle")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        
        no_edit = QLineEdit(ogrenci_no)
        no_edit.setReadOnly(True)
        ad_edit = QLineEdit(ad_soyad)
        sinif_edit = QSpinBox()
        sinif_edit.setRange(1, 6)
        sinif_edit.setValue(int(sinif))
        email_edit = QLineEdit(email)
        
        form.addRow("Öğrenci No:", no_edit)
        form.addRow("Ad Soyad:", ad_edit)
        form.addRow("Sınıf:", sinif_edit)
        form.addRow("E-posta:", email_edit)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            # Update student
            updated_data = {
                'ad_soyad': ad_edit.text().strip(),
                'sinif': sinif_edit.value(),
                'email': email_edit.text().strip()
            }
            
            result = self.ogrenci_controller.update_ogrenci(ogrenci_no, updated_data)
            
            if result['success']:
                QMessageBox.information(self, "Başarılı", result['message'])
                self.load_existing_ogrenciler()
            else:
                QMessageBox.critical(self, "Hata", result['message'])
    
    def select_all_students(self):
        """Select all students in table"""
        self.table.selectAll()
    
    def deselect_all_students(self):
        """Deselect all students"""
        self.table.clearSelection()
    
    def delete_selected_students(self):
        """Delete multiple selected students"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen silmek için en az bir öğrenci seçin!")
            return
        
        # Check if any are pending
        pending_found = False
        student_list = []
        for index in selected_rows:
            row = index.row()
            durum = self.table.item(row, 4).text()
            if durum == "Beklemede":
                pending_found = True
                break
            ogrenci_no = self.table.item(row, 0).text()
            ad_soyad = self.table.item(row, 1).text()
            student_list.append((ogrenci_no, ad_soyad))
        
        if pending_found:
            QMessageBox.warning(self, "Uyarı", "Beklemedeki öğrenciler silinemez! İptal için sayfayı yenileyin.")
            return
        
        reply = QMessageBox.question(
            self,
            "Öğrencileri Sil",
            f"{len(student_list)} öğrenciyi silmek istediğinizden emin misiniz?\n\n"
            "Bu işlem geri alınamaz!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success_count = 0
            error_count = 0
            
            for ogrenci_no, ad_soyad in student_list:
                result = self.ogrenci_controller.delete_ogrenci(ogrenci_no)
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    logger.error(f"Failed to delete {ogrenci_no}: {result['message']}")
            
            QMessageBox.information(
                self,
                "İşlem Tamamlandı",
                f"✅ {success_count} öğrenci silindi\n❌ {error_count} öğrenci silinemedi"
            )
            
            self.load_existing_ogrenciler()
    
    def edit_selected_student(self):
        """Edit selected student"""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir öğrenci seçin!")
            return
        
        row = selected_rows[0].row()
        durum = self.table.item(row, 4).text()
        
        if durum == "Beklemede":
            QMessageBox.warning(self, "Uyarı", "Beklemedeki öğrenciler düzenlenemez! Önce kaydedin.")
            return
        
        ogrenci_no = self.table.item(row, 0).text()
        ad_soyad = self.table.item(row, 1).text()
        sinif = self.table.item(row, 2).text()
        email = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
        
        # Create edit dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Öğrenci Düzenle")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        
        no_edit = QLineEdit(ogrenci_no)
        no_edit.setReadOnly(True)
        ad_edit = QLineEdit(ad_soyad)
        sinif_edit = QSpinBox()
        sinif_edit.setRange(1, 6)
        sinif_edit.setValue(int(sinif))
        email_edit = QLineEdit(email)
        
        form.addRow("Öğrenci No:", no_edit)
        form.addRow("Ad Soyad:", ad_edit)
        form.addRow("Sınıf:", sinif_edit)
        form.addRow("E-posta:", email_edit)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            # Update student
            updated_data = {
                'ad_soyad': ad_edit.text().strip(),
                'sinif': sinif_edit.value(),
                'email': email_edit.text().strip()
            }
            
            result = self.ogrenci_controller.update_ogrenci(ogrenci_no, updated_data)
            
            if result['success']:
                QMessageBox.information(self, "Başarılı", result['message'])
                self.load_existing_ogrenciler()
            else:
                QMessageBox.critical(self, "Hata", result['message'])
    
    def export_to_excel(self):
        """Export students to Excel"""
        try:
            import pandas as pd
            from datetime import datetime
            
            # Get all students
            ogrenciler = self.ogrenci_model.get_ogrenciler_by_bolum(self.bolum_id)
            
            if not ogrenciler:
                QMessageBox.warning(self, "Uyarı", "Aktarılacak öğrenci bulunamadı!")
                return
            
            # Ask for save location
            default_name = f"ogrenci_listesi_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
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
            for ogr in ogrenciler:
                data.append({
                    'Öğrenci No': ogr['ogrenci_no'],
                    'Ad Soyad': ogr['ad_soyad'],
                    'Sınıf': ogr.get('sinif', ''),
                    'E-posta': ogr.get('email', '')
                })
            
            df = pd.DataFrame(data)
            
            # Write to Excel with formatting
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Öğrenciler')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Öğrenciler']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = max_length
            
            QMessageBox.information(
                self,
                "Başarılı",
                f"Öğrenci listesi başarıyla aktarıldı!\n{len(data)} öğrenci\n\n{file_path}"
            )
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            QMessageBox.critical(self, "Hata", f"Excel aktarma hatası:\n{str(e)}")
