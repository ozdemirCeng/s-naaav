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
            
            # Filter by selected courses if specified
            selected_ders_ids = params.get('selected_ders_ids')
            if selected_ders_ids:
                dersler = [d for d in dersler if d['ders_id'] in selected_ders_ids]
            
            if not dersler:
                return {
                    'success': False,
                    'message': "Seçili ders bulunamadı!"
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
                params['sinav_suresi'],
                params['ara_suresi'],
                params.get('allowed_weekdays', [0, 1, 2, 3, 4])
            )
            
            # Calculate total capacity: time_slots × classrooms
            total_capacity = len(time_slots) * len(derslikler)
            
            if total_capacity < len(dersler):
                return {
                    'success': False,
                    'message': f"Yetersiz kapasite! {len(dersler)} ders için {len(time_slots)} slot × {len(derslikler)} derslik = {total_capacity} kapasite mevcut."
                }
            
            if progress_callback:
                progress_callback(50, "Dersler slotlara yerleştiriliyor...")
            
            # Group courses by class
            courses_by_class = {}
            for ders in dersler:
                sinif = ders.get('sinif', 1)
                if sinif not in courses_by_class:
                    courses_by_class[sinif] = []
                courses_by_class[sinif].append(ders)
            
            # Split time slots by days
            slots_by_day = {}
            for slot in time_slots:
                day = slot.date()
                if day not in slots_by_day:
                    slots_by_day[day] = []
                slots_by_day[day].append(slot)
            
            days = sorted(slots_by_day.keys())
            
            # Assign courses to time slots with parallel classroom usage
            schedule = []
            slot_usage = {}  # Track which classrooms are used in each slot
            student_schedule = {}  # Track which students have exams in each slot
            unassigned_courses = []  # Track courses that couldn't be assigned
            
            total_courses = len(dersler)
            processed = 0
            
            # Distribute each class's courses across different days
            for sinif in sorted(courses_by_class.keys()):
                class_courses = courses_by_class[sinif]
                day_index = 0
                
                for ders in class_courses:
                    processed += 1
                    
                    # Get students taking this course
                    ogrenciler = self.ogrenci_model.get_ogrenciler_by_ders(ders['ders_id'])
                    ogrenci_count = len(ogrenciler)
                    student_ids = [o['ogrenci_no'] for o in ogrenciler]
                    
                    # Debug info
                    if processed <= 3:  # Log first 3 courses for debugging
                        logger.info(f"Processing {ders['ders_kodu']}: {ogrenci_count} students")
                    
                    # Find available slot and classroom(s)
                    assigned = False
                    
                    # Try to assign to next available day (round-robin across days)
                    attempts = 0
                    while attempts < len(days) and not assigned:
                        current_day = days[day_index % len(days)]
                        day_slots = slots_by_day[current_day]
                        
                        for slot_time in day_slots:
                            slot_key = slot_time.isoformat()
                            
                            # Check for student conflicts only if there are students
                            if student_ids:
                                students_in_slot = student_schedule.get(slot_key, set())
                                has_conflict = any(sid in students_in_slot for sid in student_ids)
                                
                                if has_conflict:
                                    continue
                            
                            # Get classrooms already used in this slot
                            used_derslikler = slot_usage.get(slot_key, [])
                            
                            # Try to find single classroom first
                            for derslik in derslikler:
                                if derslik['derslik_id'] not in used_derslikler:
                                    if derslik['kapasite'] >= ogrenci_count:
                                        # Single classroom is enough
                                        exam = {
                                            'ders_id': ders['ders_id'],
                                            'ders_kodu': ders['ders_kodu'],
                                            'ders_adi': ders['ders_adi'],
                                            'tarih_saat': slot_time,
                                            'sure': params['sinav_suresi'],
                                            'derslik_id': derslik['derslik_id'],
                                            'derslik_kodu': derslik['derslik_kodu'],
                                            'ogrenci_sayisi': ogrenci_count,
                                            'sinav_tipi': params['sinav_tipi'],
                                            'bolum_id': params['bolum_id']
                                        }
                                        
                                        schedule.append(exam)
                                        
                                        if slot_key not in slot_usage:
                                            slot_usage[slot_key] = []
                                        slot_usage[slot_key].append(derslik['derslik_id'])
                                        
                                        if slot_key not in student_schedule:
                                            student_schedule[slot_key] = set()
                                        student_schedule[slot_key].update(student_ids)
                                        
                                        assigned = True
                                        break
                            
                            if assigned:
                                break
                            
                            # If single classroom not enough, try multiple classrooms
                            if not assigned:
                                available_derslikler = [d for d in derslikler if d['derslik_id'] not in used_derslikler]
                                total_capacity = sum(d['kapasite'] for d in available_derslikler)
                                
                                if total_capacity >= ogrenci_count and len(available_derslikler) > 0:
                                    # Use multiple classrooms for this exam
                                    remaining_students = ogrenci_count
                                    classrooms_used = []
                                    
                                    for derslik in available_derslikler:
                                        if remaining_students <= 0:
                                            break
                                        
                                        students_in_this_room = min(derslik['kapasite'], remaining_students)
                                        
                                        exam = {
                                            'ders_id': ders['ders_id'],
                                            'ders_kodu': ders['ders_kodu'],
                                            'ders_adi': ders['ders_adi'],
                                            'tarih_saat': slot_time,
                                            'sure': params['sinav_suresi'],
                                            'derslik_id': derslik['derslik_id'],
                                            'derslik_kodu': derslik['derslik_kodu'],
                                            'ogrenci_sayisi': students_in_this_room,
                                            'sinav_tipi': params['sinav_tipi'],
                                            'bolum_id': params['bolum_id']
                                        }
                                        
                                        schedule.append(exam)
                                        classrooms_used.append(derslik['derslik_id'])
                                        remaining_students -= students_in_this_room
                                    
                                    # Mark all classrooms as used
                                    if slot_key not in slot_usage:
                                        slot_usage[slot_key] = []
                                    slot_usage[slot_key].extend(classrooms_used)
                                    
                                    # Mark students as having exam
                                    if slot_key not in student_schedule:
                                        student_schedule[slot_key] = set()
                                    student_schedule[slot_key].update(student_ids)
                                    
                                    assigned = True
                                    logger.info(f"✅ {ders['ders_kodu']} split into {len(classrooms_used)} classrooms")
                        
                        if assigned:
                            break
                        
                        # Try next day
                        attempts += 1
                        day_index += 1
                
                    if not assigned:
                        logger.warning(f"❌ Could not assign {ders['ders_kodu']}: {ogrenci_count} students")
                        unassigned_courses.append({
                            'ders_kodu': ders['ders_kodu'],
                            'ders_adi': ders['ders_adi'],
                            'ogrenci_sayisi': ogrenci_count,
                            'sinif': ders.get('sinif', '?')
                        })
                    else:
                        # Move to next day for next course in this class
                        day_index += 1
                    
                    if progress_callback:
                        progress = 50 + int(processed / total_courses * 40)
                        progress_callback(progress, f"{ders['ders_kodu']} yerleştirildi...")
            
            if progress_callback:
                progress_callback(100, "Tamamlandı!")
            
            logger.info(f"✅ Exam schedule created: {len(schedule)} exams")
            
            # Check if all courses were assigned
            if unassigned_courses:
                # Group by class for better error message
                by_class = {}
                for course in unassigned_courses:
                    sinif = course['sinif']
                    if sinif not in by_class:
                        by_class[sinif] = []
                    by_class[sinif].append(course)
                
                error_msg = f"⚠️ {len(unassigned_courses)} ders yerleştirilemedi!\n\n"
                error_msg += "Öneriler:\n"
                error_msg += "1. Sınav tarih aralığını genişletin (daha fazla gün)\n"
                error_msg += "2. Daha fazla derslik ekleyin\n"
                error_msg += "3. Bazı dersleri programdan çıkarın\n\n"
                error_msg += "Yerleştirilemeyen dersler:\n"
                
                for sinif, courses in sorted(by_class.items()):
                    error_msg += f"\n{sinif}. Sınıf ({len(courses)} ders):\n"
                    for course in courses[:5]:  # Show max 5 per class
                        error_msg += f"  • {course['ders_kodu']} - {course['ogrenci_sayisi']} öğrenci\n"
                    if len(courses) > 5:
                        error_msg += f"  ... ve {len(courses) - 5} ders daha\n"
                
                return {
                    'success': False,
                    'message': error_msg,
                    'schedule': schedule,
                    'unassigned_courses': unassigned_courses
                }
            
            return {
                'success': True,
                'message': f"✅ {len(schedule)} sınav başarıyla programlandı",
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
        exam_duration: int,
        break_duration: int,
        allowed_weekdays: List[int] = None
    ) -> List[datetime]:
        """
        Generate available time slots for exams dynamically
        Time slots are generated based on exam_duration + break_duration
        Example: 75 min exam + 15 min break = 90 min intervals
        
        Args:
            start_date: Start date for exam period
            end_date: End date for exam period
            exam_duration: Duration of each exam in minutes
            break_duration: Break duration between exams in minutes
            allowed_weekdays: List of allowed weekdays (0=Monday, 6=Sunday)
                            If None, defaults to weekdays only (Mon-Fri)
        """
        if allowed_weekdays is None:
            allowed_weekdays = [0, 1, 2, 3, 4]  # Mon-Fri by default
        
        slots = []
        current_date = start_date
        
        # Calculate time slots based on exam duration + break
        # Start time: 09:00, slots every (exam_duration + break_duration) minutes
        slot_interval = exam_duration + break_duration  # Default: 75 + 15 = 90 minutes
        
        # Generate time slots from 09:00 to 17:45
        # With 90-minute intervals: 09:00, 10:30, 12:00, 13:30, 15:00, 16:30
        base_times = []
        start_hour = 9
        start_minute = 0
        
        current_minutes = start_hour * 60 + start_minute
        end_minutes = 17 * 60 + 45  # Last slot can start at 17:45
        
        while current_minutes <= end_minutes:
            hour = current_minutes // 60
            minute = current_minutes % 60
            base_times.append((hour, minute))
            current_minutes += slot_interval
        
        logger.info(f"Generated {len(base_times)} time slots per day: {base_times}")
        logger.info(f"Allowed weekdays: {allowed_weekdays}")
        
        while current_date <= end_date:
            weekday = current_date.weekday()  # 0=Monday, 6=Sunday
            
            # Only include allowed weekdays
            if weekday in allowed_weekdays:
                for hour, minute in base_times:
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
