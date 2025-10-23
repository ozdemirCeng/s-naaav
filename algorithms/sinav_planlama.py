"""
Sınav Planlama Algoritması
Intelligent exam scheduling with constraint satisfaction
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional
from models.database import db
from models.ders_model import DersModel
from models.derslik_model import DerslikModel
from models.ogrenci_model import OgrenciModel

logger = logging.getLogger(__name__)


class SinavPlanlama:
    """Exam scheduling algorithm"""
    
    def __init__(self):
        self.ders_model = DersModel(db)
        self.derslik_model = DerslikModel(db)
        self.ogrenci_model = OgrenciModel(db)
    
    def plan_exam_schedule(
        self, 
        params: Dict, 
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict:
        """
        Create exam schedule with constraint satisfaction
        
        Args:
            params: Scheduling parameters
                - bolum_id: Department ID
                - sinav_tipi: Exam type (Vize/Final/Bütünleme)
                - baslangic_tarih: Start date
                - bitis_tarih: End date
                - gun_basina_sinav: Exams per day
                - sinav_suresi: Exam duration (minutes)
                - ara_suresi: Break duration (minutes)
            progress_callback: Optional callback for progress updates
                
        Returns:
            Dictionary with success status and schedule data
        """
        try:
            if progress_callback:
                progress_callback(10, "Dersler yükleniyor...")
            
            # Get courses for the department
            dersler = self.ders_model.get_dersler_by_bolum(params['bolum_id'])
            
            if not dersler:
                return {
                    'success': False,
                    'message': "Bölümde ders bulunamadı!"
                }
            
            if progress_callback:
                progress_callback(20, "Derslikler yükleniyor...")
            
            # Get available classrooms
            derslikler = self.derslik_model.get_derslikler_by_bolum(params['bolum_id'])
            
            if not derslikler:
                return {
                    'success': False,
                    'message': "Derslik bulunamadı!"
                }
            
            if progress_callback:
                progress_callback(30, "Sınav takvimi oluşturuluyor...")
            
            # Generate time slots
            time_slots = self._generate_time_slots(
                params['baslangic_tarih'],
                params['bitis_tarih'],
                params['gun_basina_sinav'],
                params['sinav_suresi'],
                params['ara_suresi']
            )
            
            if len(time_slots) < len(dersler):
                return {
                    'success': False,
                    'message': f"Yetersiz zaman aralığı! {len(dersler)} ders için {len(time_slots)} slot mevcut."
                }
            
            if progress_callback:
                progress_callback(50, "Dersler slotlara yerleştiriliyor...")
            
            # Assign courses to time slots
            schedule = []
            derslik_index = 0
            
            for i, ders in enumerate(dersler):
                if i >= len(time_slots):
                    break
                
                # Get student count for this course
                ogrenciler = self.ogrenci_model.get_ogrenciler_by_ders(ders['ders_id'])
                ogrenci_count = len(ogrenciler)
                
                # Find suitable classroom
                derslik = self._find_suitable_derslik(derslikler, ogrenci_count, derslik_index)
                derslik_index = (derslik_index + 1) % len(derslikler)
                
                exam = {
                    'ders_id': ders['ders_id'],
                    'ders_kodu': ders['ders_kodu'],
                    'ders_adi': ders['ders_adi'],
                    'tarih_saat': time_slots[i],
                    'sure': params['sinav_suresi'],
                    'derslik_id': derslik['derslik_id'],
                    'derslik_kodu': derslik['derslik_kodu'],
                    'ogrenci_sayisi': ogrenci_count,
                    'sinav_tipi': params['sinav_tipi'],
                    'bolum_id': params['bolum_id']
                }
                
                schedule.append(exam)
                
                if progress_callback:
                    progress = 50 + int((i + 1) / len(dersler) * 40)
                    progress_callback(progress, f"{ders['ders_kodu']} yerleştirildi...")
            
            if progress_callback:
                progress_callback(100, "Tamamlandı!")
            
            logger.info(f"✅ Exam schedule created: {len(schedule)} exams")
            
            return {
                'success': True,
                'message': f"{len(schedule)} sınav programlandı",
                'schedule': schedule
            }
            
        except Exception as e:
            logger.error(f"Exam scheduling error: {e}")
            return {
                'success': False,
                'message': f"Program oluşturma hatası: {str(e)}"
            }
    
    def _generate_time_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        exams_per_day: int,
        exam_duration: int,
        break_duration: int
    ) -> List[datetime]:
        """Generate available time slots for exams"""
        slots = []
        current_date = start_date
        
        # Standard exam times (9:00, 13:00, 16:00)
        base_times = [
            (9, 0),
            (13, 0),
            (16, 0)
        ]
        
        while current_date <= end_date:
            # Skip weekends (optional)
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                for i in range(min(exams_per_day, len(base_times))):
                    hour, minute = base_times[i]
                    slot_time = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    slots.append(slot_time)
            
            current_date += timedelta(days=1)
        
        return slots
    
    def _find_suitable_derslik(
        self, 
        derslikler: List[Dict], 
        ogrenci_count: int,
        start_index: int = 0
    ) -> Dict:
        """Find suitable classroom for given student count"""
        # Sort classrooms by capacity
        sorted_derslikler = sorted(derslikler, key=lambda x: x['kapasite'])
        
        # Find first classroom that fits
        for i in range(start_index, len(sorted_derslikler)):
            derslik = sorted_derslikler[i]
            if derslik['kapasite'] >= ogrenci_count:
                return derslik
        
        # If no suitable classroom found, return largest one
        return sorted_derslikler[-1]
    
    def validate_schedule(self, schedule: List[Dict]) -> Dict:
        """Validate exam schedule for conflicts"""
        conflicts = []
        
        # Check for time conflicts
        for i, exam1 in enumerate(schedule):
            for j, exam2 in enumerate(schedule[i+1:], i+1):
                # Same time, same classroom
                if (exam1['tarih_saat'] == exam2['tarih_saat'] and
                    exam1['derslik_id'] == exam2['derslik_id']):
                    conflicts.append({
                        'type': 'classroom_conflict',
                        'exam1': exam1['ders_kodu'],
                        'exam2': exam2['ders_kodu'],
                        'message': 'Aynı anda aynı derslik kullanılıyor'
                    })
        
        if conflicts:
            return {
                'success': False,
                'conflicts': conflicts,
                'message': f"{len(conflicts)} çakışma bulundu"
            }
        
        return {
            'success': True,
            'message': "Program geçerli"
        }
