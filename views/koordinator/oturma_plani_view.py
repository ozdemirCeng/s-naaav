"""
Oturma Planı View - Seating Plan Management
Allows creating and visualizing seating arrangements for exams
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGridLayout, QScrollArea, QFrame, QGroupBox, QFileDialog,
    QDialog, QListWidget, QListWidgetItem, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from models.database import db
from models.sinav_model import SinavModel
from models.derslik_model import DerslikModel
from models.ogrenci_model import OgrenciModel
from utils.modern_dialogs import ModernMessageBox, sanitize_filename
from algorithms.oturma_planlama import OturmaPlanlama

logger = logging.getLogger(__name__)


class OturmaPlaniView(QWidget):
    """Seating plan view for exam arrangements"""

    def __init__(self, user_data: Dict):
        super().__init__()
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id')

        # Models
        self.sinav_model = SinavModel(db)
        self.derslik_model = DerslikModel(db)
        self.ogrenci_model = OgrenciModel(db)

        # Current selection
        self.selected_sinav = None
        self.seating_data = {}  # {ogrenci_no: {derslik_id, sira, sutun}}
        self.seating_data_sinav_id = None  # Track which exam the seating data belongs to

        self.init_ui()
        self.load_exams()
    
    def showEvent(self, event):
        """Refresh exam list when view is shown"""
        super().showEvent(event)
        # Reload exams to show newly created ones
        self.load_exams()

    def init_ui(self):
        """Initialize user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("📋 Oturma Planı Yönetimi")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #1f2937; padding: 10px;")
        layout.addWidget(header)

        # Info card
        info = QLabel("Sınav programındaki dersler için oturma düzeni oluşturun ve görselleştirin.")
        info.setStyleSheet("""
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 12px;
            border-radius: 6px;
            color: #1e40af;
            font-size: 13px;
        """)
        layout.addWidget(info)

        # Split layout: Exam list on left, seating plan on right
        content_layout = QHBoxLayout()

        # Left: Exam list
        exam_group = QGroupBox("Sınav Listesi")
        exam_group.setStyleSheet("""
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
        exam_layout = QVBoxLayout(exam_group)

        self.exams_table = QTableWidget()
        self.exams_table.setColumnCount(5)
        self.exams_table.setHorizontalHeaderLabels(['Ders Kodu', 'Ders Adı', 'Tarih/Saat', 'Derslikler', 'İşlem'])
        self.exams_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.exams_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.exams_table.setSelectionMode(QTableWidget.SingleSelection)
        self.exams_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.exams_table.itemSelectionChanged.connect(self.on_exam_selected)
        self.exams_table.setMinimumWidth(600)
        exam_layout.addWidget(self.exams_table)

        content_layout.addWidget(exam_group, 2)

        # Right: Seating plan visualization
        plan_group = QGroupBox("Oturma Düzeni")
        plan_group.setStyleSheet("""
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
        plan_layout = QVBoxLayout(plan_group)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.create_plan_btn = QPushButton("🎯 Oturma Düzeni Oluştur")
        self.create_plan_btn.setFixedHeight(40)
        self.create_plan_btn.setEnabled(False)
        self.create_plan_btn.setStyleSheet("""
            QPushButton {
                background: #10b981;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background: #059669; }
            QPushButton:disabled { background: #9ca3af; }
        """)
        self.create_plan_btn.clicked.connect(self.create_seating_plan)
        btn_layout.addWidget(self.create_plan_btn)

        self.export_visual_btn = QPushButton("📄 Görsel PDF (Oturma Düzeni)")
        self.export_visual_btn.setFixedHeight(40)
        self.export_visual_btn.setEnabled(False)
        self.export_visual_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background: #2563eb; }
            QPushButton:disabled { background: #9ca3af; }
        """)
        self.export_visual_btn.clicked.connect(self.export_visual_pdf)
        btn_layout.addWidget(self.export_visual_btn)

        self.export_list_btn = QPushButton("📋 Liste PDF (Tablo)")
        self.export_list_btn.setFixedHeight(40)
        self.export_list_btn.setEnabled(False)
        self.export_list_btn.setStyleSheet("""
            QPushButton {
                background: #10b981;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background: #059669; }
            QPushButton:disabled { background: #9ca3af; }
        """)
        self.export_list_btn.clicked.connect(self.export_list_pdf)
        btn_layout.addWidget(self.export_list_btn)

        btn_layout.addStretch()
        plan_layout.addLayout(btn_layout)

        # Scroll area for seating visualization
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #e5e7eb; border-radius: 6px; background: white; }")

        self.seating_widget = QWidget()
        self.seating_layout = QVBoxLayout(self.seating_widget)
        self.seating_layout.setAlignment(Qt.AlignCenter)

        scroll.setWidget(self.seating_widget)
        plan_layout.addWidget(scroll)

        # Student list
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(5)
        self.students_table.setHorizontalHeaderLabels(['Öğrenci No', 'Ad Soyad', 'Derslik', 'Sıra', 'Sütun'])
        self.students_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.students_table.setMaximumHeight(200)
        plan_layout.addWidget(self.students_table)

        content_layout.addWidget(plan_group, 3)

        layout.addLayout(content_layout)

    def load_exams(self):
        """Load all exams for the department"""
        try:
            # Get all exam programs for department
            programs = self.sinav_model.get_programs_by_bolum(self.bolum_id)

            if not programs:
                logger.info("Oturma Planı: Henüz sınav programı yok")
                return

            # Get exams from all programs
            all_exams = []
            for program in programs:
                exams = self.sinav_model.get_sinavlar_by_program(program['program_id'])
                for exam in exams:
                    exam['program_id'] = program['program_id']
                    exam['program_adi'] = program['program_adi']
                    all_exams.append(exam)

            logger.info(f"Oturma Planı: {len(all_exams)} sınav yüklendi")
            self.exams_table.setRowCount(0)

            for exam in all_exams:
                row = self.exams_table.rowCount()
                self.exams_table.insertRow(row)

                self.exams_table.setItem(row, 0, QTableWidgetItem(exam.get('ders_kodu', '')))
                self.exams_table.setItem(row, 1, QTableWidgetItem(exam.get('ders_adi', '')))

                tarih_saat = exam.get('tarih_saat', '')
                if isinstance(tarih_saat, str):
                    try:
                        dt = datetime.fromisoformat(tarih_saat)
                        tarih_saat = dt.strftime('%d.%m.%Y %H:%M')
                    except:
                        pass
                elif hasattr(tarih_saat, 'strftime'):
                    tarih_saat = tarih_saat.strftime('%d.%m.%Y %H:%M')

                self.exams_table.setItem(row, 2, QTableWidgetItem(str(tarih_saat)))
                self.exams_table.setItem(row, 3, QTableWidgetItem(exam.get('derslik_adi', exam.get('derslik_kodu', ''))))

                # Add change classroom button
                change_btn = QPushButton("🔄 Derslik Değiştir")
                change_btn.setStyleSheet("""
                    QPushButton {
                        background: #f59e0b;
                        color: white;
                        font-weight: bold;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 11px;
                    }
                    QPushButton:hover { background: #d97706; }
                """)
                change_btn.clicked.connect(lambda checked=False, e=exam: self.change_classroom(e))
                self.exams_table.setCellWidget(row, 4, change_btn)

                # Store exam data
                for col in range(4):
                    item = self.exams_table.item(row, col)
                    if item:
                        item.setData(Qt.UserRole, exam)

        except Exception as e:
            logger.error(f"Error loading exams: {e}", exc_info=True)
            ModernMessageBox.error(self, "Yükleme Hatası", "Sınavlar yüklenirken bir hata oluştu.", f"Hata detayı:\n{str(e)}")

    def on_exam_selected(self):
        """Handle exam selection"""
        selected_items = self.exams_table.selectedItems()
        if not selected_items:
            self.selected_sinav = None
            self.create_plan_btn.setEnabled(False)
            self.export_visual_btn.setEnabled(False)
            self.export_list_btn.setEnabled(False)
            self.clear_seating_plan()
            logger.info("❌ No exam selected - all buttons disabled")
            return

        # Get exam data from first item
        exam_data = selected_items[0].data(Qt.UserRole)
        if not exam_data:
            logger.warning("⚠️ Selected item has no exam data")
            return

        # Check if this is a different exam
        is_different_exam = (
            not self.selected_sinav or 
            self.selected_sinav.get('sinav_id') != exam_data.get('sinav_id')
        )

        # Save old exam info before updating
        old_exam_kodu = self.selected_sinav.get('ders_kodu', '') if self.selected_sinav else ''
        old_sinav_id = self.selected_sinav.get('sinav_id') if self.selected_sinav else None
        
        self.selected_sinav = exam_data
        new_sinav_id = exam_data.get('sinav_id')
        new_ders_kodu = exam_data.get('ders_kodu', '')
        
        logger.info(f"📋 Exam selected: {new_ders_kodu} (Sınav ID: {new_sinav_id})")
        
        self.create_plan_btn.setEnabled(True)

        # Only clear if selecting a different exam
        if is_different_exam:
            # Warn if there was seating data
            if self.seating_data and self.seating_data_sinav_id:
                QMessageBox.information(
                    self,
                    "Sınav Değişti",
                    f"⚠️ Farklı bir sınav seçtiniz!\n\n"
                    f"Önceki: {old_exam_kodu} (ID: {old_sinav_id})\n"
                    f"Yeni: {new_ders_kodu} (ID: {new_sinav_id})\n\n"
                    f"Önceki oturma düzeni temizlendi.\n"
                    f"Yeni sınav için oturma düzeni oluşturmanız gerekiyor."
                )
            
            self.load_existing_seating_plan()  # This calls clear_seating_plan()
        elif self.seating_data and self.seating_data_sinav_id == new_sinav_id:
            # Same exam and we have VALID seating data for THIS exam
            logger.info(f"✅ Same exam re-selected, keeping seating data. Exam: {new_ders_kodu} (ID: {new_sinav_id})")
            self.export_visual_btn.setEnabled(True)
            self.export_list_btn.setEnabled(True)
            
            # Update tooltips
            exam_info_text = f"Oturma düzeni: {new_ders_kodu} (Sınav ID: {new_sinav_id})"
            self.export_visual_btn.setToolTip(f"📄 {exam_info_text}\n\nGörsel PDF olarak indir")
            self.export_list_btn.setToolTip(f"📋 {exam_info_text}\n\nListe PDF olarak indir")
        elif self.seating_data and self.seating_data_sinav_id != new_sinav_id:
            # CRITICAL: Same exam selected but seating data is for DIFFERENT exam!
            logger.error(f"❌ MISMATCH: Selected exam {new_sinav_id} but seating data is for exam {self.seating_data_sinav_id}!")
            logger.error(f"   This shouldn't happen - clearing seating data")
            self.clear_seating_plan()
        else:
            # Same exam but no seating data
            logger.info(f"ℹ️ Same exam selected but no seating data. Exam: {new_ders_kodu} (ID: {new_sinav_id})")
            self.export_visual_btn.setEnabled(False)
            self.export_list_btn.setEnabled(False)

    def load_existing_seating_plan(self):
        """Load existing seating plan if available"""
        # TODO: Check database for existing seating plan
        # For now, just clear and enable creation
        self.clear_seating_plan()

    def create_seating_plan(self):
        """Create seating arrangement for selected exam"""
        if not self.selected_sinav:
            return

        try:
            # Get students for this exam
            ders_id = self.selected_sinav.get('ders_id')
            sinav_id = self.selected_sinav.get('sinav_id')

            students = self.ogrenci_model.get_ogrenciler_by_ders(ders_id)

            if not students:
                ModernMessageBox.information(self, "Bilgi", "Bu derse kayıtlı öğrenci bulunamadı!")
                return

            # Get classroom(s) for this exam
            classrooms = self._get_exam_classrooms(sinav_id)

            if not classrooms:
                ModernMessageBox.warning(self, "Uyarı", "Bu sınav için derslik bilgisi bulunamadı!")
                return

            # Check total capacity
            total_capacity = sum(c.get('kapasite', 0) for c in classrooms)

            if len(students) > total_capacity:
                confirmed = ModernMessageBox.question(
                    self,
                    "Kapasite Uyarısı",
                    f"⚠️ Öğrenci sayısı derslik kapasitesini aşıyor!\n\n"
                    f"Sadece {total_capacity} öğrenci yerleştirilebilir.\n"
                    f"Devam etmek istiyor musunuz?",
                    f"Öğrenci: {len(students)}\nKapasite: {total_capacity}\nFark: {len(students) - total_capacity}"
                )
                if not confirmed:
                    return

            # Create seating arrangement using OturmaPlanlama algorithm
            oturma_planlama = OturmaPlanlama()
            plan_list = oturma_planlama._generate_multi_classroom_plan(students, classrooms)

            if not plan_list:
                ModernMessageBox.warning(self, "Uyarı", "Oturma düzeni oluşturulamadı!")
                return

            # Convert list to dict format {ogrenci_no: {derslik_id, sira, sutun, ad_soyad, derslik_adi}}
            seating_data = {}
            for item in plan_list:
                seating_data[item['ogrenci_no']] = {
                    'derslik_id': item['derslik_id'],
                    'derslik_adi': item['derslik_adi'],
                    'sira': item['satir'],
                    'sutun': item['sutun'],
                    'ad_soyad': item['ad_soyad']
                }
            
            self.seating_data = seating_data
            self.seating_data_sinav_id = sinav_id  # Track which exam this data belongs to
            
            logger.info(f"✅ Oturma düzeni oluşturuldu: {len(seating_data)} öğrenci")

            # Visualize seating plan
            self.visualize_seating_plan(classrooms, seating_data)

            # Update student list
            self.update_student_list(students, seating_data)

            # Enable export buttons with clear tooltips
            self.export_visual_btn.setEnabled(True)
            self.export_list_btn.setEnabled(True)
            
            # Add tooltips showing which exam this data is for
            exam_info_text = f"Oturma düzeni: {self.selected_sinav.get('ders_kodu', '')} (Sınav ID: {sinav_id})"
            self.export_visual_btn.setToolTip(f"📄 {exam_info_text}\n\nGörsel PDF olarak indir")
            self.export_list_btn.setToolTip(f"📋 {exam_info_text}\n\nListe PDF olarak indir")

            # Show result message
            placed_count = len(seating_data)
            if placed_count < len(students):
                ModernMessageBox.warning(
                    self,
                    "Kısmi Başarı",
                    f"⚠️ {placed_count}/{len(students)} öğrenci yerleştirildi!\n\n"
                    f"Kapasite yetersiz olduğu için {len(students) - placed_count} öğrenci yerleştirilemedi.\n\n"
                    f"Şimdi PDF butonlarını kullanarak indirebilirsiniz.",
                    f"Yerleştirilen: {placed_count}\nYerleştirilemeyen: {len(students) - placed_count}"
                )
            else:
                ModernMessageBox.success(
                    self,
                    "Başarılı",
                    f"{len(students)} öğrenci için oturma düzeni oluşturuldu!\n\n"
                    f"📄 Görsel PDF: Derslik yerleşimi\n"
                    f"📋 Liste PDF: Öğrenci tablosu\n\n"
                    f"PDF butonlarını kullanarak indirebilirsiniz.",
                    f"Toplam öğrenci: {len(students)}\nDerslik sayısı: {len(classrooms)}"
                )

        except Exception as e:
            logger.error(f"Error creating seating plan: {e}", exc_info=True)
            ModernMessageBox.error(self, "Planlama Hatası", "Oturma düzeni oluşturulurken bir hata oluştu.", f"Hata detayı:\n{str(e)}")

    def _get_exam_classrooms(self, sinav_id: int) -> List[Dict]:
        """Get classrooms assigned to an exam"""
        try:
            query = """
                SELECT dr.derslik_id, dr.derslik_kodu, dr.derslik_adi, 
                       dr.kapasite, dr.satir_sayisi, dr.sutun_sayisi, dr.sira_yapisi
                FROM sinav_derslikleri sd
                JOIN derslikler dr ON sd.derslik_id = dr.derslik_id
                WHERE sd.sinav_id = %s
                ORDER BY dr.derslik_adi
            """
            result = db.execute_query(query, (sinav_id,), fetch=True)
            return result if result else []
        except Exception as e:
            logger.error(f"Error getting exam classrooms: {e}", exc_info=True)
            return []

    def visualize_seating_plan(self, classrooms: List[Dict], seating_data: Dict):
        """Visualize seating arrangement with corridor groups"""
        # Clear existing VISUALIZATION ONLY (don't touch seating_data!)
        logger.info("🎨 Clearing old visualization widgets (keeping seating data)")
        while self.seating_layout.count():
            child = self.seating_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for classroom in classrooms:
            derslik_id = classroom['derslik_id']
            rows = classroom.get('satir_sayisi', 10)
            cols = classroom.get('sutun_sayisi', 6)
            kapasite = classroom.get('kapasite', 60)
            sira_yapisi = classroom.get('sira_yapisi', 3)  # 2'li veya 3'lü grup

            # Classroom header
            header = QLabel(f"🏫 {classroom.get('derslik_adi', classroom.get('derslik_kodu'))} (Kapasite: {kapasite})")
            header.setFont(QFont("Segoe UI", 14, QFont.Bold))
            header.setStyleSheet("color: #1f2937; padding: 10px;")
            self.seating_layout.addWidget(header)

            # Find max used row for this classroom
            max_used_row = 0
            for ogrenci_no, data in seating_data.items():
                if data['derslik_id'] == derslik_id:
                    max_used_row = max(max_used_row, data['sira'])

            # Only show used rows (no extra rows to reduce widget count)
            display_rows = max_used_row if max_used_row > 0 else min(5, rows)
            
            # Count students in this classroom
            students_in_classroom = sum(1 for data in seating_data.values() if data['derslik_id'] == derslik_id)
            logger.info(f"    Görselleştirme: {classroom.get('derslik_adi')} - {students_in_classroom} öğrenci, {display_rows} satır gösteriliyor")

            # Reverse seat data for lookup
            seat_lookup = {}
            for ogrenci_no, data in seating_data.items():
                if data['derslik_id'] == derslik_id:
                    key = (data['sira'], data['sutun'])
                    seat_lookup[key] = ogrenci_no

            # Create grid for seats with corridor grouping
            grid = QGridLayout()
            grid.setSpacing(3)

            # Calculate total visual columns (with corridors + window + door) based on sira_yapisi
            corridor_count = (cols - 1) // sira_yapisi
            total_visual_cols = cols + corridor_count + 2  # +1 for window, +1 for door

            # Front label (Board)
            front_label = QLabel("📺 TAHTA")
            front_label.setAlignment(Qt.AlignCenter)
            front_label.setStyleSheet("""
                background: #fef3c7;
                border: 2px solid #f59e0b;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
                color: #92400e;
            """)
            grid.addWidget(front_label, 0, 0, 1, total_visual_cols)

            # Left side - Windows
            window_label = QLabel("🪟\nP\nE\nN\nC\nE\nR\nE")
            window_label.setAlignment(Qt.AlignCenter)
            window_label.setStyleSheet("""
                background: #dbeafe;
                border: 2px solid #3b82f6;
                border-radius: 4px;
                padding: 4px;
                font-weight: bold;
                color: #1e40af;
                font-size: 10px;
            """)
            grid.addWidget(window_label, 1, 0, display_rows, 1)

            # Shift columns by 1 to accommodate window label
            col_offset = 1

            for row in range(1, display_rows + 1):
                # Add corridor space based on sira_yapisi (2'li or 3'lü groups)
                visual_col = col_offset
                for col in range(1, cols + 1):
                    # Add corridor space after every sira_yapisi seats
                    if col > 1 and (col - 1) % sira_yapisi == 0:
                        spacer = QLabel("│")
                        spacer.setAlignment(Qt.AlignCenter)
                        spacer.setStyleSheet("color: #d1d5db; font-size: 20px;")
                        grid.addWidget(spacer, row, visual_col)
                        visual_col += 1

                    seat_btn = QPushButton()
                    seat_btn.setFixedSize(65, 65)

                    key = (row, col)
                    if key in seat_lookup:
                        ogrenci_no = seat_lookup[key]
                        ad_soyad = seating_data[ogrenci_no].get('ad_soyad', '')
                        seat_btn.setText(f"{ogrenci_no}\n{ad_soyad[:12]}")
                        seat_btn.setStyleSheet("""
                            QPushButton {
                                background: #dbeafe;
                                border: 2px solid #3b82f6;
                                border-radius: 6px;
                                font-size: 9px;
                                font-weight: bold;
                                color: #1e40af;
                            }
                            QPushButton:hover {
                                background: #bfdbfe;
                            }
                        """)
                        seat_btn.setToolTip(f"{ad_soyad}\nÖğrenci No: {ogrenci_no}\nSıra: {row}, Sütun: {col}")
                    else:
                        # Empty seat - make it visually distinct
                        seat_btn.setText("✗\nBOŞ")
                        seat_btn.setStyleSheet("""
                            QPushButton {
                                background: #fee2e2;
                                border: 2px dashed #ef4444;
                                border-radius: 6px;
                                font-size: 11px;
                                font-weight: bold;
                                color: #991b1b;
                            }
                        """)
                        seat_btn.setToolTip(f"Boş Koltuk - Sıra: {row}, Sütun: {col}")

                    grid.addWidget(seat_btn, row, visual_col)
                    visual_col += 1

            # Right side - Door (at the back)
            door_label = QLabel("🚪\nK\nA\nP\nI")
            door_label.setAlignment(Qt.AlignCenter)
            door_label.setStyleSheet("""
                background: #fef3c7;
                border: 2px solid #f59e0b;
                border-radius: 4px;
                padding: 4px;
                font-weight: bold;
                color: #92400e;
                font-size: 10px;
            """)
            # Place door at the back (last few rows)
            door_start_row = max(1, display_rows - 3)
            grid.addWidget(door_label, door_start_row, visual_col, min(4, display_rows), 1)

            grid_widget = QWidget()
            grid_widget.setLayout(grid)
            self.seating_layout.addWidget(grid_widget)

            # Add spacing between classrooms
            self.seating_layout.addSpacing(20)

    def update_student_list(self, students: List[Dict], seating_data: Dict):
        """Update student list table"""
        self.students_table.setRowCount(0)

        for student in students:
            ogrenci_no = student['ogrenci_no']
            if ogrenci_no not in seating_data:
                continue

            row = self.students_table.rowCount()
            self.students_table.insertRow(row)

            seat_info = seating_data[ogrenci_no]

            self.students_table.setItem(row, 0, QTableWidgetItem(str(ogrenci_no)))
            self.students_table.setItem(row, 1, QTableWidgetItem(student.get('ad_soyad', '')))
            self.students_table.setItem(row, 2, QTableWidgetItem(seat_info['derslik_adi']))
            self.students_table.setItem(row, 3, QTableWidgetItem(str(seat_info['sira'])))
            self.students_table.setItem(row, 4, QTableWidgetItem(str(seat_info['sutun'])))

    def clear_seating_plan(self):
        """Clear seating plan visualization"""
        # Clear visualization widgets
        while self.seating_layout.count():
            child = self.seating_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Clear data
        self.students_table.setRowCount(0)
        self.seating_data = {}
        self.seating_data_sinav_id = None
        self.export_visual_btn.setEnabled(False)
        self.export_list_btn.setEnabled(False)

    def export_visual_pdf(self):
        """Export visual seating plan (classroom layout) to PDF"""
        if not self.selected_sinav:
            ModernMessageBox.warning(self, "Uyarı", "Lütfen önce bir sınav seçin!")
            logger.warning("Export failed: No exam selected")
            return
        
        if not self.seating_data:
            logger.error(f"❌ VISUAL PDF Export failed: No seating data!")
            logger.error(f"   Selected exam: {self.selected_sinav.get('ders_kodu')} (ID: {self.selected_sinav.get('sinav_id')})")
            logger.error(f"   self.seating_data length: {len(self.seating_data)}")
            logger.error(f"   self.seating_data_sinav_id: {self.seating_data_sinav_id}")
            ModernMessageBox.warning(self, "Uyarı", "Önce oturma düzeni oluşturun!\n\n'🎯 Oturma Düzeni Oluştur' butonuna tıklayın.")
            return
        
        # CRITICAL: Check if seating data matches selected exam
        current_sinav_id = self.selected_sinav.get('sinav_id')
        if self.seating_data_sinav_id != current_sinav_id:
            QMessageBox.warning(
                self,
                "Yanlış Sınav!",
                f"⚠️ DİKKAT: Oturma düzeni farklı bir sınav için oluşturulmuş!\n\n"
                f"Seçili sınav: {self.selected_sinav.get('ders_kodu', '')}\n\n"
                f"Önce bu sınav için oturma düzeni oluşturun:\n"
                f"'🎯 Oturma Düzeni Oluştur' butonuna tıklayın."
            )
            logger.error(f"Export failed: Seating data for exam {self.seating_data_sinav_id} but trying to export for exam {current_sinav_id}")
            # Disable export buttons
            self.export_visual_btn.setEnabled(False)
            self.export_list_btn.setEnabled(False)
            return

        try:
            from utils.export_utils import ExportUtils

            ders_kodu = sanitize_filename(self.selected_sinav.get('ders_kodu', 'DERS'))
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Görsel Oturma Planı PDF",
                f"oturma_duzen_{ders_kodu}_{timestamp}.pdf",
                "PDF Files (*.pdf)"
            )

            if not file_path:
                return

            # Prepare data for visual export
            # Format exam info with proper date string
            exam_info = self.selected_sinav.copy()
            tarih_saat = exam_info.get('tarih_saat', '')
            if isinstance(tarih_saat, str):
                try:
                    dt = datetime.fromisoformat(tarih_saat)
                    exam_info['tarih_saat'] = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    pass
            elif hasattr(tarih_saat, 'strftime'):
                exam_info['tarih_saat'] = tarih_saat.strftime('%d.%m.%Y %H:%M')
            
            export_data = {
                'type': 'oturma_plani',
                'title': f"{self.selected_sinav.get('ders_adi', '')} - Oturma Düzeni",
                'exam_info': exam_info,
                'seating_data': self.seating_data,
                'classrooms': self._get_exam_classrooms(self.selected_sinav.get('sinav_id'))
            }

            if ExportUtils.export_to_pdf(export_data, file_path):
                ModernMessageBox.success(
                    self,
                    "Başarılı",
                    "Görsel oturma düzeni PDF olarak kaydedildi!",
                    f"Dosya konumu:\n{file_path}"
                )
            else:
                ModernMessageBox.warning(self, "Uyarı", "PDF oluşturulamadı!")

        except Exception as e:
            logger.error(f"Error exporting visual PDF: {e}", exc_info=True)
            ModernMessageBox.error(self, "Export Hatası", "PDF oluşturulurken bir hata oluştu.", f"Hata detayı:\n{str(e)}")

    def export_list_pdf(self):
        """Export student list (table format) to PDF"""
        if not self.selected_sinav:
            ModernMessageBox.warning(self, "Uyarı", "Lütfen önce bir sınav seçin!")
            logger.warning("Export failed: No exam selected")
            return
        
        if not self.seating_data:
            logger.error(f"❌ LIST PDF Export failed: No seating data!")
            logger.error(f"   Selected exam: {self.selected_sinav.get('ders_kodu')} (ID: {self.selected_sinav.get('sinav_id')})")
            logger.error(f"   self.seating_data length: {len(self.seating_data)}")
            logger.error(f"   self.seating_data_sinav_id: {self.seating_data_sinav_id}")
            ModernMessageBox.warning(self, "Uyarı", "Önce oturma düzeni oluşturun!\n\n'🎯 Oturma Düzeni Oluştur' butonuna tıklayın.")
            return
        
        # CRITICAL: Check if seating data matches selected exam
        current_sinav_id = self.selected_sinav.get('sinav_id')
        if self.seating_data_sinav_id != current_sinav_id:
            QMessageBox.warning(
                self,
                "Yanlış Sınav!",
                f"⚠️ DİKKAT: Oturma düzeni farklı bir sınav için oluşturulmuş!\n\n"
                f"Seçili sınav: {self.selected_sinav.get('ders_kodu', '')}\n\n"
                f"Önce bu sınav için oturma düzeni oluşturun:\n"
                f"'🎯 Oturma Düzeni Oluştur' butonuna tıklayın."
            )
            logger.error(f"Export failed: Seating data for exam {self.seating_data_sinav_id} but trying to export for exam {current_sinav_id}")
            # Disable export buttons
            self.export_visual_btn.setEnabled(False)
            self.export_list_btn.setEnabled(False)
            return

        try:
            from utils.export_utils import ExportUtils

            ders_kodu = sanitize_filename(self.selected_sinav.get('ders_kodu', 'DERS'))
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Öğrenci Listesi PDF",
                f"oturma_liste_{ders_kodu}_{timestamp}.pdf",
                "PDF Files (*.pdf)"
            )

            if not file_path:
                return

            # Prepare data for list export
            # Format exam info with proper date string
            exam_info = self.selected_sinav.copy()
            tarih_saat = exam_info.get('tarih_saat', '')
            if isinstance(tarih_saat, str):
                try:
                    dt = datetime.fromisoformat(tarih_saat)
                    exam_info['tarih_saat'] = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    pass
            elif hasattr(tarih_saat, 'strftime'):
                exam_info['tarih_saat'] = tarih_saat.strftime('%d.%m.%Y %H:%M')
            
            export_data = {
                'type': 'oturma_liste',
                'title': f"{self.selected_sinav.get('ders_adi', '')} - Öğrenci Oturma Listesi",
                'exam_info': exam_info,
                'seating_data': self.seating_data,
                'classrooms': self._get_exam_classrooms(self.selected_sinav.get('sinav_id'))
            }

            if ExportUtils.export_to_pdf(export_data, file_path):
                ModernMessageBox.success(
                    self,
                    "Başarılı",
                    "Öğrenci listesi PDF olarak kaydedildi!",
                    f"Dosya konumu:\n{file_path}"
                )
            else:
                ModernMessageBox.warning(self, "Uyarı", "PDF oluşturulamadı!")

        except Exception as e:
            logger.error(f"Error exporting list PDF: {e}", exc_info=True)
            ModernMessageBox.error(self, "Export Hatası", "PDF oluşturulurken bir hata oluştu.", f"Hata detayı:\n{str(e)}")

    def change_classroom(self, exam: Dict):
        """Change classroom for selected exam"""
        try:
            sinav_id = exam.get('sinav_id')
            if not sinav_id:
                return

            # Get all available classrooms for this department
            all_classrooms = self.derslik_model.get_derslikler_by_bolum(self.bolum_id)

            if not all_classrooms:
                ModernMessageBox.warning(self, "Uyarı", "Sistemde derslik bulunamadı!")
                return

            # Get currently assigned classrooms
            current_classrooms = self._get_exam_classrooms(sinav_id)
            current_ids = [c['derslik_id'] for c in current_classrooms]

            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Derslik Değiştir - {exam.get('ders_adi', '')}")
            dialog.setMinimumWidth(500)
            dialog.setMinimumHeight(400)

            layout = QVBoxLayout(dialog)

            # Info label
            info = QLabel(f"📚 Ders: {exam.get('ders_kodu', '')} - {exam.get('ders_adi', '')}")
            info.setStyleSheet("font-weight: bold; padding: 10px; background: #eff6ff; border-radius: 6px;")
            layout.addWidget(info)

            # Current classrooms
            current_label = QLabel("Mevcut Derslikler:")
            current_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            layout.addWidget(current_label)

            current_text = ", ".join([c.get('derslik_adi', c.get('derslik_kodu', '')) for c in current_classrooms])
            current_info = QLabel(current_text if current_text else "Derslik atanmamış")
            current_info.setStyleSheet("padding: 8px; background: #fef3c7; border-radius: 4px; color: #92400e;")
            layout.addWidget(current_info)

            # New classroom selection
            new_label = QLabel("Yeni Derslik Seçin:")
            new_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
            layout.addWidget(new_label)

            # Classroom list with checkboxes
            classroom_list = QListWidget()
            classroom_list.setSelectionMode(QListWidget.MultiSelection)

            for classroom in all_classrooms:
                item_text = f"{classroom.get('derslik_kodu', '')} - {classroom.get('derslik_adi', '')} (Kapasite: {classroom.get('kapasite', 0)})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, classroom['derslik_id'])

                # Pre-select current classrooms
                if classroom['derslik_id'] in current_ids:
                    item.setSelected(True)
                    item.setBackground(QColor("#dbeafe"))

                classroom_list.addItem(item)

            layout.addWidget(classroom_list)

            # Buttons
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            # Show dialog
            if dialog.exec() == QDialog.Accepted:
                # Get selected classrooms
                selected_items = classroom_list.selectedItems()
                selected_ids = [item.data(Qt.UserRole) for item in selected_items]

                if not selected_ids:
                    ModernMessageBox.warning(self, "Uyarı", "Lütfen en az bir derslik seçin!")
                    return

                # Update database
                self._update_exam_classrooms(sinav_id, selected_ids)

                # Save current selection and seating data
                saved_sinav = self.selected_sinav
                saved_seating_data = self.seating_data.copy() if self.seating_data else {}

                # Reload exams
                self.load_exams()

                # Restore selection and seating data if it was the same exam
                if saved_sinav and saved_sinav.get('sinav_id') == sinav_id:
                    self.selected_sinav = saved_sinav
                    # Only clear seating data (it's invalid now with new classrooms)
                    self.clear_seating_plan()
                    # Re-select the row
                    for row in range(self.exams_table.rowCount()):
                        item = self.exams_table.item(row, 0)
                        if item and item.data(Qt.UserRole) and item.data(Qt.UserRole).get('sinav_id') == sinav_id:
                            self.exams_table.selectRow(row)
                            break

                ModernMessageBox.information(self, "Başarılı", "✅ Derslik değişikliği başarıyla kaydedildi!\n\nYeni derslik düzenine göre oturma planını yeniden oluşturun.")

        except Exception as e:
            logger.error(f"Error changing classroom: {e}", exc_info=True)
            ModernMessageBox.error(self, "Değiştirme Hatası", "Derslik değiştirilirken bir hata oluştu.", f"Hata detayı:\n{str(e)}")

    def _update_exam_classrooms(self, sinav_id: int, classroom_ids: List[int]):
        """Update classrooms for an exam"""
        try:
            # Use context manager for transaction
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete existing assignments
                delete_query = "DELETE FROM sinav_derslikleri WHERE sinav_id = %s"
                cursor.execute(delete_query, (sinav_id,))

                # Insert new assignments
                insert_query = "INSERT INTO sinav_derslikleri (sinav_id, derslik_id) VALUES (%s, %s)"
                for derslik_id in classroom_ids:
                    cursor.execute(insert_query, (sinav_id, derslik_id))

                # Commit transaction
                conn.commit()
                cursor.close()

            logger.info(f"Updated classrooms for exam {sinav_id}: {classroom_ids}")

        except Exception as e:
            logger.error(f"Error updating exam classrooms: {e}", exc_info=True)
            raise