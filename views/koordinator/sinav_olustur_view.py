"""
Sınav Oluştur View - REFACTORED
Sadece UI ve kullanıcı etkileşimi
İş mantığı controller ve algorithm katmanlarında
"""

import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QMessageBox, QProgressBar
)
from PySide6.QtCore import QThread, Signal

from models.database import db
from models.sinav_model import SinavModel
from models.ders_model import DersModel
from models.derslik_model import DerslikModel
from models.ogrenci_model import OgrenciModel
from controllers.sinav_controller import SinavController
from algorithms.sinav_planlama import SinavPlanlama
from algorithms.scoring_system import SinavProgramScorer
from algorithms.attempt_manager import AttemptManager

logger = logging.getLogger(__name__)


class SinavPlanlamaThread(QThread):
    """Thread for exam planning with multiple attempts"""
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, params, use_multiple_attempts=True):
        super().__init__()
        self.params = params
        self.use_multiple_attempts = use_multiple_attempts

    def run(self):
        try:
            if self.use_multiple_attempts:
                # Çoklu deneme modı
                scorer = SinavProgramScorer()
                attempt_manager = AttemptManager(scorer)
                planner = SinavPlanlama()

                result = attempt_manager.run_multiple_attempts(
                    planning_function=planner.plan_exam_schedule,
                    params=self.params,
                    max_attempts=self.params.get('max_attempts', 50),
                    progress_callback=self.progress.emit
                )
            else:
                # Tek deneme modı (hızlı test için)
                planner = SinavPlanlama()
                result = planner.plan_exam_schedule(
                    self.params,
                    progress_callback=self.progress.emit
                )

            self.finished.emit(result)

        except Exception as e:
            logger.error(f"Planning thread error: {e}", exc_info=True)
            self.error.emit(str(e))


class SinavOlusturView(QWidget):
    """Modern exam schedule creation view - REFACTORED"""

    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.bolum_id = user_data.get('bolum_id', 1)

        # Models
        self.sinav_model = SinavModel(db)
        self.ders_model = DersModel(db)
        self.derslik_model = DerslikModel(db)
        self.ogrenci_model = OgrenciModel(db)

        # Controller
        self.controller = SinavController(
            self.sinav_model,
            self.ders_model,
            self.derslik_model
        )

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Setup UI - KOD AYNI KALACAK"""
        # ... Mevcut UI kodu aynı kalacak
        # Sadece create_schedule metodunu değiştireceğiz
        pass

    def create_schedule(self):
        """
        Create exam schedule - REFACTORED
        Tüm iş mantığı kaldırıldı, sadece veri toplama ve thread başlatma
        """
        # 1. VALIDATE USER INPUTS
        validation = self._validate_inputs()
        if not validation['valid']:
            QMessageBox.warning(
                self,
                "Geçersiz Giriş",
                validation['message']
            )
            return

        # 2. COLLECT PARAMETERS
        params = self._collect_parameters()

        # 3. SHOW PROGRESS
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Sınav programı oluşturuluyor...")
        self.create_btn.setEnabled(False)

        # 4. START PLANNING THREAD
        use_multiple = params.get('use_multiple_attempts', True)
        self.planning_thread = SinavPlanlamaThread(params, use_multiple)
        self.planning_thread.progress.connect(self.on_planning_progress)
        self.planning_thread.finished.connect(self.on_planning_finished)
        self.planning_thread.error.connect(self.on_planning_error)
        self.planning_thread.start()

    def _validate_inputs(self) -> Dict:
        """Validate user inputs"""
        # Date validation
        if self.baslangic_tarih.dateTime() >= self.bitis_tarih.dateTime():
            return {
                'valid': False,
                'message': "Bitiş tarihi başlangıçtan sonra olmalıdır!"
            }

        # Days validation
        allowed_weekdays = [
            day for day, checkbox in self.gun_checkboxes.items()
            if checkbox.isChecked()
        ]
        if not allowed_weekdays:
            return {
                'valid': False,
                'message': "En az bir gün seçmelisiniz!"
            }

        # Courses validation
        selected_ders_ids = [
            ders_id for ders_id, checkbox in self.ders_checkboxes.items()
            if checkbox.isChecked()
        ]
        if not selected_ders_ids:
            return {
                'valid': False,
                'message': "En az bir ders seçmelisiniz!"
            }

        return {'valid': True}

    def _collect_parameters(self) -> Dict:
        """Collect all parameters from UI"""
        # Selected courses
        selected_ders_ids = [
            ders_id for ders_id, checkbox in self.ders_checkboxes.items()
            if checkbox.isChecked()
        ]

        # Custom durations
        ders_sureleri = {}
        for ders_id, spinbox in self.ders_duration_spinboxes.items():
            if ders_id in selected_ders_ids:
                ders_sureleri[ders_id] = spinbox.value()

        # Allowed weekdays
        allowed_weekdays = [
            day for day, checkbox in self.gun_checkboxes.items()
            if checkbox.isChecked()
        ]

        # Time strings
        ilk_sinav = f"{self.ilk_sinav_saat.value():02d}:{self.ilk_sinav_dakika.value():02d}"
        son_sinav = f"{self.son_sinav_saat.value():02d}:{self.son_sinav_dakika.value():02d}"
        ogle_baslangic = f"{self.ogle_baslangic_saat.value():02d}:{self.ogle_baslangic_dakika.value():02d}"
        ogle_bitis = f"{self.ogle_bitis_saat.value():02d}:{self.ogle_bitis_dakika.value():02d}"

        return {
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
            'max_attempts': 50,  # Sabit veya UI'dan alınabilir
            'use_multiple_attempts': True  # Çoklu deneme aktif
        }

    def on_planning_progress(self, percent, message):
        """Update planning progress"""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def on_planning_finished(self, result):
        """
        Handle planning completion - REFACTORED
        Sadece sonuç gösterimi, kaydetme controller'da
        """
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.create_btn.setEnabled(True)

        # Cleanup thread
        if hasattr(self, 'planning_thread') and self.planning_thread:
            self.planning_thread.quit()
            self.planning_thread.wait()
            self.planning_thread = None

        if not result.get('success'):
            self._show_error(result)
            return

        schedule = result.get('schedule', [])
        if not schedule:
            QMessageBox.warning(
                self,
                "Uyarı",
                "Boş program oluşturuldu!"
            )
            return

        # Show result dialog with score
        self._show_result_dialog(result)

    def on_planning_error(self, error_msg):
        """Handle planning error"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.create_btn.setEnabled(True)

        # Cleanup thread
        if hasattr(self, 'planning_thread') and self.planning_thread:
            self.planning_thread.quit()
            self.planning_thread.wait()
            self.planning_thread = None

        QMessageBox.critical(
            self,
            "Hata",
            f"Planlama hatası:\n{error_msg}"
        )

    def _show_result_dialog(self, result: Dict):
        """Show result dialog with scoring details"""
        from views.program_result_dialog import ProgramResultDialog

        params = {
            'bolum_id': self.bolum_id,
            'sinav_tipi': self.sinav_tipi_combo.currentText()
        }

        dialog = ProgramResultDialog(
            schedule_data=result['schedule'],
            params=params,
            score_result=result.get('score_details'),
            parent=self
        )

        dialog_result = dialog.exec()

        if dialog_result:
            # Refresh programs list
            self.load_existing_programs()
            self.refresh_main_window_ui()

    def _show_error(self, result: Dict):
        """Show error message"""
        message = result.get('message', 'Program oluşturulamadı!')
        warnings = result.get('warnings', [])
        details = "\n".join(warnings) if warnings else "Detay bilgi bulunmuyor"

        QMessageBox.critical(
            self,
            "Program Oluşturulamadı",
            f"{message}\n\n{details}"
        )

    # ... Diğer UI metodları aynı kalacak (load_data, populate_course_list, vb.)