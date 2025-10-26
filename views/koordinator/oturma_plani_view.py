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

        self.init_ui()
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
                return

            # Get exams from all programs
            all_exams = []
            for program in programs:
                exams = self.sinav_model.get_sinavlar_by_program(program['program_id'])
                for exam in exams:
                    exam['program_id'] = program['program_id']
                    exam['program_adi'] = program['program_adi']
                    all_exams.append(exam)

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
                change_btn.clicked.connect(lambda checked, e=exam: self.change_classroom(e))
                self.exams_table.setCellWidget(row, 4, change_btn)

                # Store exam data
                for col in range(4):
                    item = self.exams_table.item(row, col)
                    if item:
                        item.setData(Qt.UserRole, exam)

            logger.info(f"Loaded {len(all_exams)} exams for seating plans")

        except Exception as e:
            logger.error(f"Error loading exams: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Sınavlar yüklenirken hata:\n{str(e)}")

    def on_exam_selected(self):
        """Handle exam selection"""
        selected_items = self.exams_table.selectedItems()
        if not selected_items:
            self.selected_sinav = None
            self.create_plan_btn.setEnabled(False)
            self.export_visual_btn.setEnabled(False)
            self.export_list_btn.setEnabled(False)
            self.clear_seating_plan()
            return

        # Get exam data from first item
        exam_data = selected_items[0].data(Qt.UserRole)
        if not exam_data:
            return

        self.selected_sinav = exam_data
        self.create_plan_btn.setEnabled(True)

        # Check if seating plan already exists
        self.load_existing_seating_plan()

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
                QMessageBox.information(self, "Bilgi", "Bu derse kayıtlı öğrenci bulunamadı!")
                return

            # Get classroom(s) for this exam
            classrooms = self._get_exam_classrooms(sinav_id)

            if not classrooms:
                QMessageBox.warning(self, "Uyarı", "Bu sınav için derslik bilgisi bulunamadı!")
                return

            # Check total capacity
            total_capacity = sum(c.get('kapasite', 0) for c in classrooms)

            if len(students) > total_capacity:
                reply = QMessageBox.question(
                    self,
                    "Kapasite Uyarısı",
                    f"⚠️ Uyarı: Öğrenci sayısı ({len(students)}) derslik kapasitesini ({total_capacity}) aşıyor!\n\n"
                    f"Sadece {total_capacity} öğrenci yerleştirilebilir.\n\n"
                    f"Devam etmek istiyor musunuz?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

            # Create seating arrangement
            seating_data = self._assign_seats(students, classrooms)

            if not seating_data:
                QMessageBox.warning(self, "Uyarı", "Oturma düzeni oluşturulamadı!")
                return

            self.seating_data = seating_data

            # Visualize seating plan
            self.visualize_seating_plan(classrooms, seating_data)

            # Update student list
            self.update_student_list(students, seating_data)

            self.export_visual_btn.setEnabled(True)
            self.export_list_btn.setEnabled(True)

            # Show result message
            placed_count = len(seating_data)
            if placed_count < len(students):
                QMessageBox.warning(
                    self,
                    "Kısmi Başarı",
                    f"⚠️ {placed_count}/{len(students)} öğrenci yerleştirildi!\n\n"
                    f"Kapasite yetersiz olduğu için {len(students) - placed_count} öğrenci yerleştirilemedi."
                )
            else:
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"✅ {len(students)} öğrenci için oturma düzeni oluşturuldu!"
                )

        except Exception as e:
            logger.error(f"Error creating seating plan: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Oturma düzeni oluşturulurken hata:\n{str(e)}")

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

    def _assign_seats(self, students: List[Dict], classrooms: List[Dict]) -> Dict:
        """Assign students to seats in classrooms with capacity check and smart distribution"""
        seating = {}
        student_idx = 0
        total_students = len(students)

        # Sort students by name for consistent arrangement
        students = sorted(students, key=lambda x: x.get('ad_soyad', ''))

        # Calculate total available capacity
        total_capacity = sum(c.get('kapasite', 0) for c in classrooms)

        if total_students > total_capacity:
            logger.warning(f"Not enough capacity! Students: {total_students}, Capacity: {total_capacity}")
            # Will place as many as possible

        for classroom in classrooms:
            if student_idx >= total_students:
                break

            derslik_id = classroom['derslik_id']
            kapasite = classroom.get('kapasite', 60)
            rows = classroom.get('satir_sayisi', 10)
            cols = classroom.get('sutun_sayisi', 6)

            # Calculate how many students to place in this classroom
            remaining_students = total_students - student_idx
            students_for_this_room = min(remaining_students, kapasite)

            # Calculate required rows (don't use all rows if not needed)
            required_rows = (students_for_this_room + cols - 1) // cols
            required_rows = min(required_rows, rows)

            logger.info(f"Classroom {classroom.get('derslik_adi')}: {students_for_this_room} students in {required_rows} rows")

            # TRUE Zigzag pattern to minimize cheating:
            # Row 1: Students at columns 1, 3, 5 (leave 2, 4, 6 empty)
            # Row 2: Students at columns 2, 4, 6 (leave 1, 3, 5 empty)
            # Row 3: Students at columns 1, 3, 5 (leave 2, 4, 6 empty)
            # This creates a checkerboard pattern
            placed_in_room = 0

            # Recalculate required rows with zigzag (only half capacity per row)
            effective_cols_per_row = (cols + 1) // 2  # half of columns per row
            required_rows_zigzag = (students_for_this_room + effective_cols_per_row - 1) // effective_cols_per_row
            required_rows_zigzag = min(required_rows_zigzag, rows)

            for row in range(1, required_rows_zigzag + 1):
                if student_idx >= total_students or placed_in_room >= students_for_this_room:
                    break

                # Zigzag: odd rows use odd columns, even rows use even columns
                if row % 2 == 1:
                    # Odd rows: 1, 3, 5, ... (left to right)
                    col_list = [c for c in range(1, cols + 1) if c % 2 == 1]
                else:
                    # Even rows: 2, 4, 6, ... (left to right)
                    col_list = [c for c in range(1, cols + 1) if c % 2 == 0]

                for col in col_list:
                    if student_idx >= total_students or placed_in_room >= students_for_this_room:
                        break

                    student = students[student_idx]
                    seating[student['ogrenci_no']] = {
                        'derslik_id': derslik_id,
                        'derslik_adi': classroom.get('derslik_adi', classroom.get('derslik_kodu')),
                        'sira': row,
                        'sutun': col,
                        'ad_soyad': student.get('ad_soyad', '')
                    }
                    student_idx += 1
                    placed_in_room += 1

        if student_idx < total_students:
            logger.warning(f"Could not place all students! Placed: {student_idx}/{total_students}")

        return seating

    def visualize_seating_plan(self, classrooms: List[Dict], seating_data: Dict):
        """Visualize seating arrangement with corridor groups"""
        # Clear existing layout
        self.clear_seating_plan()

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

            # Only show used rows + 1 extra
            display_rows = min(max_used_row + 1, rows) if max_used_row > 0 else rows

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
                        # Empty seat - make it visually distinct (zigzag pattern)
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
                        seat_btn.setToolTip(f"Boş Koltuk (ZigZag) - Sıra: {row}, Sütun: {col}")

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
        while self.seating_layout.count():
            child = self.seating_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.students_table.setRowCount(0)
        self.seating_data = {}
        self.export_visual_btn.setEnabled(False)
        self.export_list_btn.setEnabled(False)

    def export_visual_pdf(self):
        """Export visual seating plan (classroom layout) to PDF"""
        if not self.selected_sinav or not self.seating_data:
            QMessageBox.warning(self, "Uyarı", "Önce oturma düzeni oluşturun!")
            return

        try:
            from utils.export_utils import ExportUtils

            ders_kodu = self.selected_sinav.get('ders_kodu', 'DERS')
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
            export_data = {
                'type': 'oturma_plani',
                'title': f"{self.selected_sinav.get('ders_adi', '')} - Oturma Düzeni",
                'exam_info': self.selected_sinav,
                'seating_data': self.seating_data,
                'classrooms': self._get_exam_classrooms(self.selected_sinav.get('sinav_id'))
            }

            if ExportUtils.export_to_pdf(export_data, file_path):
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"✅ Görsel oturma düzeni PDF olarak kaydedildi:\n{file_path}"
                )
            else:
                QMessageBox.warning(self, "Uyarı", "PDF oluşturulamadı!")

        except Exception as e:
            logger.error(f"Error exporting visual PDF: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"PDF oluşturulurken hata:\n{str(e)}")

    def export_list_pdf(self):
        """Export student list (table format) to PDF"""
        if not self.selected_sinav or not self.seating_data:
            QMessageBox.warning(self, "Uyarı", "Önce oturma düzeni oluşturun!")
            return

        try:
            from utils.export_utils import ExportUtils

            ders_kodu = self.selected_sinav.get('ders_kodu', 'DERS')
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
            export_data = {
                'type': 'oturma_liste',
                'title': f"{self.selected_sinav.get('ders_adi', '')} - Öğrenci Oturma Listesi",
                'exam_info': self.selected_sinav,
                'seating_data': self.seating_data,
                'classrooms': self._get_exam_classrooms(self.selected_sinav.get('sinav_id'))
            }

            if ExportUtils.export_to_pdf(export_data, file_path):
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"✅ Öğrenci listesi PDF olarak kaydedildi:\n{file_path}"
                )
            else:
                QMessageBox.warning(self, "Uyarı", "PDF oluşturulamadı!")

        except Exception as e:
            logger.error(f"Error exporting list PDF: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"PDF oluşturulurken hata:\n{str(e)}")

    def change_classroom(self, exam: Dict):
        """Change classroom for selected exam"""
        try:
            sinav_id = exam.get('sinav_id')
            if not sinav_id:
                return

            # Get all available classrooms
            all_classrooms = self.derslik_model.get_all_derslikler()

            if not all_classrooms:
                QMessageBox.warning(self, "Uyarı", "Sistemde derslik bulunamadı!")
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
                    QMessageBox.warning(self, "Uyarı", "Lütfen en az bir derslik seçin!")
                    return

                # Update database
                self._update_exam_classrooms(sinav_id, selected_ids)

                # Reload exams
                self.load_exams()

                # Clear current seating plan if this exam was selected
                if self.selected_sinav and self.selected_sinav.get('sinav_id') == sinav_id:
                    self.clear_seating_plan()

                QMessageBox.information(self, "Başarılı", "✅ Derslik değişikliği başarıyla kaydedildi!")

        except Exception as e:
            logger.error(f"Error changing classroom: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Derslik değiştirilirken hata:\n{str(e)}")

    def _update_exam_classrooms(self, sinav_id: int, classroom_ids: List[int]):
        """Update classrooms for an exam"""
        try:
            # Start transaction
            db.connection.autocommit = False

            # Delete existing assignments
            delete_query = "DELETE FROM sinav_derslikleri WHERE sinav_id = %s"
            db.execute_query(delete_query, (sinav_id,))

            # Insert new assignments
            insert_query = "INSERT INTO sinav_derslikleri (sinav_id, derslik_id) VALUES (%s, %s)"
            for derslik_id in classroom_ids:
                db.execute_query(insert_query, (sinav_id, derslik_id))

            # Commit transaction
            db.connection.commit()
            db.connection.autocommit = True

            logger.info(f"Updated classrooms for exam {sinav_id}: {classroom_ids}")

        except Exception as e:
            # Rollback on error
            db.connection.rollback()
            db.connection.autocommit = True
            logger.error(f"Error updating exam classrooms: {e}", exc_info=True)
            raise