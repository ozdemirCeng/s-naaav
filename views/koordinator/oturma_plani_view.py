"""
Oturma Planı (Seating Plan) View
Professional interface for generating student seating plans
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QMessageBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar, QGridLayout,
    QScrollArea, QTabWidget
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
        """Setup UI with scroll"""
        # Main scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Set scroll widget at the end
        scroll.setWidget(scroll_content)
        
        # Add scroll to main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
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
            
            try:
                # Get detailed classroom info
                derslikler = self.sinav_model.get_sinav_derslikleri(sinav['sinav_id'])
                derslik_info = []
                total_capacity = 0
                
                for dr in derslikler:
                    derslik_info.append(f"{dr['derslik_adi']} ({dr['kapasite']} kişi, {dr['satir_sayisi']}x{dr['sutun_sayisi']})")
                    total_capacity += dr['kapasite']
                
                derslik_text = '\n   '.join(derslik_info) if derslik_info else 'Derslik bilgisi yok'
                ogrenci_sayisi = sinav.get('ogrenci_sayisi', 0)
                
                logger.info(f"📊 Sınav seçildi: {sinav['ders_kodu']}, {len(derslikler)} derslik")
                
                self.exam_info_label.setText(
                    f"📚 Ders: {sinav['ders_kodu']} - {sinav['ders_adi']}\n"
                    f"📅 Tarih: {sinav['tarih_saat']}\n"
                    f"👥 Öğrenci Sayısı: {ogrenci_sayisi}\n"
                    f"🏛 Derslik(ler) ({len(derslikler)} adet - Toplam {total_capacity} kişi):\n   {derslik_text}"
                )
                self.exam_info_label.setVisible(True)
                self.generate_btn.setEnabled(True)
            except Exception as e:
                logger.error(f"Error loading classroom info: {e}", exc_info=True)
                self.exam_info_label.setText(f"❌ Derslik bilgisi yüklenemedi: {str(e)}")
                self.exam_info_label.setVisible(True)
                self.generate_btn.setEnabled(False)
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
        """Display generated seating plan with visual classroom layouts"""
        self.results_group.setVisible(True)
        
        # Clear existing content
        self.results_table.setRowCount(0)
        
        # Get classroom info from the current plan
        if not hasattr(self, 'sinavlar') or self.sinav_combo.currentIndex() < 0:
            return
        
        sinav = self.sinavlar[self.sinav_combo.currentIndex()]
        derslikler = self.sinav_model.get_sinav_derslikleri(sinav['sinav_id'])
        
        # Create tab widget for visual layouts if not exists
        if not hasattr(self, 'visual_tabs'):
            self.visual_tabs = QTabWidget()
            self.results_group.layout().insertWidget(0, self.visual_tabs)
        else:
            # Clear existing tabs
            self.visual_tabs.clear()
        
        # Tab 1: Visual Layout
        visual_tab = QWidget()
        visual_layout = QVBoxLayout(visual_tab)
        visual_layout.setSpacing(20)
        
        # Group plan by classroom
        from collections import defaultdict
        classroom_plans = defaultdict(list)
        for seat in plan:
            classroom_plans[seat['derslik_id']].append(seat)
        
        # Create visual layout for each classroom
        for derslik in derslikler:
            derslik_id = derslik['derslik_id']
            if derslik_id not in classroom_plans:
                continue
            
            # Classroom header
            header = QLabel(f"🏛 {derslik['derslik_adi']} - {derslik['satir_sayisi']} Sıra × {derslik['sutun_sayisi']} Sütun")
            header.setStyleSheet("font-size: 14px; font-weight: bold; color: #2563eb; padding: 8px;")
            visual_layout.addWidget(header)
            
            # Create grid visualization
            grid_widget = self.create_classroom_grid(
                derslik['satir_sayisi'],
                derslik['sutun_sayisi'],
                classroom_plans[derslik_id]
            )
            visual_layout.addWidget(grid_widget)
        
        visual_layout.addStretch()
        
        # Wrap in scroll area
        scroll = QScrollArea()
        scroll.setWidget(visual_tab)
        scroll.setWidgetResizable(True)
        self.visual_tabs.addTab(scroll, "🖼️ Görsel Düzen")
        
        # Tab 2: List View (existing table)
        list_tab = QWidget()
        list_layout = QVBoxLayout(list_tab)
        
        # Move table to list tab
        self.results_table.setParent(None)
        list_layout.addWidget(self.results_table)
        self.visual_tabs.addTab(list_tab, "📋 Liste Görünümü")
        
        # Sort by classroom, then row, then column
        sorted_plan = sorted(plan, key=lambda x: (x.get('derslik_adi', ''), x.get('satir', 0), x.get('sutun', 0)))
        
        for row, oturma in enumerate(sorted_plan):
            self.results_table.insertRow(row)
            
            self.results_table.setItem(row, 0, QTableWidgetItem(str(oturma.get('ogrenci_no', ''))))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(oturma.get('ad_soyad', ''))))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(oturma.get('derslik_adi', oturma.get('derslik_kodu', '')))))
            
            satir_item = QTableWidgetItem(str(oturma.get('satir', '')))
            satir_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(row, 3, satir_item)
            
            sutun_item = QTableWidgetItem(str(oturma.get('sutun', '')))
            sutun_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(row, 4, sutun_item)
    
    def create_classroom_grid(self, rows: int, cols: int, seating_plan: list) -> QWidget:
        """Create visual grid representation of classroom seating"""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        
        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Gösterge:"))
        
        occupied_label = QLabel("■ Dolu")
        occupied_label.setStyleSheet("color: #10b981; font-weight: bold;")
        legend_layout.addWidget(occupied_label)
        
        empty_label = QLabel("□ Boş")
        empty_label.setStyleSheet("color: #9ca3af; font-weight: bold;")
        legend_layout.addWidget(empty_label)
        
        legend_layout.addStretch()
        layout.addLayout(legend_layout)
        
        # Create seating map
        seat_map = {}
        for seat in seating_plan:
            key = (seat['satir'], seat['sutun'])
            seat_map[key] = seat
        
        # Grid
        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setContentsMargins(8, 8, 8, 8)
        
        # Add board/front indicator
        board_label = QLabel("📋 TAHTA / ÖN")
        board_label.setAlignment(Qt.AlignCenter)
        board_label.setStyleSheet("""
            background: #3b82f6;
            color: white;
            font-weight: bold;
            padding: 8px;
            border-radius: 4px;
        """)
        grid.addWidget(board_label, 0, 0, 1, cols)
        
        # Create seats
        for row in range(1, rows + 1):
            for col in range(1, cols + 1):
                seat_widget = QFrame()
                seat_widget.setFixedSize(80, 60)
                
                seat_layout = QVBoxLayout(seat_widget)
                seat_layout.setContentsMargins(4, 4, 4, 4)
                seat_layout.setSpacing(2)
                
                key = (row, col)
                if key in seat_map:
                    # Occupied seat
                    student = seat_map[key]
                    seat_widget.setStyleSheet("""
                        QFrame {
                            background: #d1fae5;
                            border: 2px solid #10b981;
                            border-radius: 6px;
                        }
                    """)
                    
                    # Student info
                    no_label = QLabel(f"🎓 {student['ogrenci_no']}")
                    no_label.setStyleSheet("font-size: 9px; font-weight: bold; color: #065f46;")
                    no_label.setAlignment(Qt.AlignCenter)
                    
                    # Truncate name if too long
                    name = student['ad_soyad']
                    if len(name) > 12:
                        name = name[:10] + "..."
                    name_label = QLabel(name)
                    name_label.setStyleSheet("font-size: 8px; color: #047857;")
                    name_label.setAlignment(Qt.AlignCenter)
                    name_label.setWordWrap(True)
                    
                    seat_layout.addWidget(no_label)
                    seat_layout.addWidget(name_label)
                else:
                    # Empty seat
                    seat_widget.setStyleSheet("""
                        QFrame {
                            background: #f3f4f6;
                            border: 1px dashed #d1d5db;
                            border-radius: 6px;
                        }
                    """)
                    
                    empty_label = QLabel("Boş")
                    empty_label.setStyleSheet("font-size: 9px; color: #9ca3af;")
                    empty_label.setAlignment(Qt.AlignCenter)
                    seat_layout.addWidget(empty_label)
                
                # Add row and column numbers
                position_label = QLabel(f"S{row}:Sü{col}")
                position_label.setStyleSheet("font-size: 7px; color: #6b7280;")
                position_label.setAlignment(Qt.AlignCenter)
                seat_layout.addWidget(position_label)
                
                grid.addWidget(seat_widget, row, col - 1)  # row offset by 1 for board
        
        layout.addLayout(grid)
        
        # Statistics
        stats_label = QLabel(f"📊 Toplam: {len(seating_plan)} öğrenci / {rows * cols} koltuk (Doluluk: %{int(len(seating_plan) / (rows * cols) * 100)})")
        stats_label.setStyleSheet("color: #6b7280; font-size: 11px; padding: 8px;")
        layout.addWidget(stats_label)
        
        return container
    
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
