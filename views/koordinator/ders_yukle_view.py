"""
Ders Yükleme (Course Upload) View
Professional interface for uploading and managing courses from Excel
"""

import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from models.database import db
from models.ders_model import DersModel
from models.ogrenci_model import OgrenciModel
from controllers.ders_controller import DersController
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
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Ders Listesi Yönetimi 📚")
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
        info_layout.setSpacing(8)
        
        info_text = QLabel(
            "Excel dosyası şu sütunları içermelidir:\n"
            "• Ders Kodu (örn: BMU101)\n"
            "• Ders Adı (örn: Programlamaya Giriş)\n"
            "• Kredi (örn: 3)\n"
            "• Yarıyıl (örn: 1)\n"
            "• Ders Yapısı (Zorunlu/Seçmeli)"
        )
        info_text.setStyleSheet("color: #6b7280; font-size: 12px;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_card)
        
        # Splitter for courses and students
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Courses table
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Ders Kodu", "Ders Adı", "Kredi", "Yarıyıl", "Ders Yapısı", "Durum"
        ])
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_course_students)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 120)
        self.table.setColumnWidth(5, 100)
        
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
        
        layout.addWidget(splitter)
        
        # Stats
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Segoe UI", 10))
        self.stats_label.setStyleSheet("color: #6b7280; padding: 8px;")
        layout.addWidget(self.stats_label)
    
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
        
        for row, ders in enumerate(dersler):
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(ders.get('ders_kodu', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(str(ders.get('ders_adi', ''))))
            
            kredi_item = QTableWidgetItem(str(ders.get('kredi', '')))
            kredi_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, kredi_item)
            
            yariyil_item = QTableWidgetItem(str(ders.get('yariyil', '')))
            yariyil_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, yariyil_item)
            
            yapisi_item = QTableWidgetItem(str(ders.get('ders_yapisi', '')))
            yapisi_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, yapisi_item)
            
            durum = "✅ Kayıtlı" if existing else "⏳ Beklemede"
            durum_item = QTableWidgetItem(durum)
            durum_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, durum_item)
    
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
        """Handle loaded Excel data"""
        if not dersler:
            QMessageBox.warning(self, "Uyarı", "Excel dosyasında ders bulunamadı!")
            return
        
        self.pending_dersler = dersler
        self.populate_table(dersler, existing=False)
        self.update_stats(0, len(dersler))
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Dersleri Kaydet",
            f"{len(dersler)} ders yüklendi. Veritabanına kaydetmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.save_dersler()
    
    def on_excel_error(self, error_msg):
        """Handle Excel loading error"""
        QMessageBox.critical(self, "Hata", f"Excel dosyası yüklenirken hata oluştu:\n{error_msg}")
    
    def save_dersler(self):
        """Save courses to database"""
        if not self.pending_dersler:
            return
        
        try:
            success_count = 0
            error_count = 0
            
            for ders in self.pending_dersler:
                ders['bolum_id'] = self.bolum_id
                result = self.ders_controller.create_ders(ders)
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    logger.warning(f"Failed to save course: {ders['ders_kodu']} - {result['message']}")
            
            QMessageBox.information(
                self,
                "İşlem Tamamlandı",
                f"✅ {success_count} ders kaydedildi\n❌ {error_count} ders kaydedilemedi"
            )
            
            self.pending_dersler = []
            self.load_existing_dersler()
            
        except Exception as e:
            logger.error(f"Error saving courses: {e}")
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
        
        # Check if any are pending
        pending_found = False
        course_list = []
        for index in selected_rows:
            row = index.row()
            durum = self.table.item(row, 5).text()
            if durum == "Beklemede":
                pending_found = True
                break
            ders_kodu = self.table.item(row, 0).text()
            ders_adi = self.table.item(row, 1).text()
            course_list.append((ders_kodu, ders_adi))
        
        if pending_found:
            QMessageBox.warning(self, "Uyarı", "Beklemedeki dersler silinemez! İptal için sayfayı yenileyin.")
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
        durum = self.table.item(row, 5).text()
        
        if durum == "Beklemede":
            QMessageBox.warning(self, "Uyarı", "Beklemedeki dersler silinemez! İptal için sayfayı yenileyin.")
            return
        
        ders_kodu = self.table.item(row, 0).text()
        ders_adi = self.table.item(row, 1).text()
        
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
