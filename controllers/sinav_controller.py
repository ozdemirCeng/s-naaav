"""
Sınav (Exam) Controller
Business logic for exam schedule management
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class SinavController:
    """Exam schedule business logic controller"""
    
    def __init__(self, sinav_model, ders_model, derslik_model):
        self.sinav_model = sinav_model
        self.ders_model = ders_model
        self.derslik_model = derslik_model
    
    def create_exam_program(self, program_data: Dict) -> Dict:
        """Create exam program"""
        try:
            # Validate data
            if not program_data.get('program_adi'):
                return {'success': False, 'message': "Program adı gereklidir!"}
            
            # Create program
            program_id = self.sinav_model.create_program(program_data)
            
            return {
                'success': True,
                'message': f"Sınav programı başarıyla oluşturuldu!",
                'program_id': program_id
            }
            
        except Exception as e:
            logger.error(f"Error creating exam program: {e}")
            return {'success': False, 'message': str(e)}
    
    def save_exam_schedule(self, schedule: List[Dict]) -> Dict:
        """Save exam schedule to database"""
        try:
            if not schedule:
                return {'success': False, 'message': "Boş program kaydedilemez!"}
            
            # DEBUG: Check for duplicate courses in schedule
            from collections import Counter
            ders_ids = [exam.get('ders_id') for exam in schedule]
            ders_counts = Counter(ders_ids)
            duplicates = {ders_id: count for ders_id, count in ders_counts.items() if count > 1}
            
            if duplicates:
                logger.warning(f"⚠️ Found duplicate ders_id in schedule: {duplicates}")
                # Group by time to see if they're at the same time (OK) or different times (ERROR)
                for ders_id, count in duplicates.items():
                    times = [str(exam.get('tarih_saat')) for exam in schedule if exam.get('ders_id') == ders_id]
                    unique_times = set(times)
                    if len(unique_times) > 1:
                        logger.error(f"❌ CRITICAL: ders_id {ders_id} scheduled at {len(unique_times)} different times: {unique_times}")
                    else:
                        logger.info(f"✅ OK: ders_id {ders_id} appears {count} times but all at same time (multi-classroom)")
            
            # First, create a program
            # Find earliest and latest dates in schedule
            all_dates = [exam.get('tarih_saat') for exam in schedule]
            all_dates = [d if isinstance(d, datetime) else datetime.fromisoformat(d) for d in all_dates]
            baslangic_tarihi = min(all_dates).date()
            bitis_tarihi = max(all_dates).date()
            
            program_data = {
                'bolum_id': schedule[0].get('bolum_id'),
                'program_adi': f"Sınav Programı - {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
                'sinav_tipi': schedule[0].get('sinav_tipi', 'Final'),
                'baslangic_tarihi': baslangic_tarihi,
                'bitis_tarihi': bitis_tarihi,
                'aktif': True
            }
            
            program_result = self.create_exam_program(program_data)
            
            if not program_result['success']:
                return program_result
            
            program_id = program_result['program_id']
            
            # Group exams by (ders_id, tarih_saat) - same course at same time uses multiple classrooms
            from collections import defaultdict
            exam_groups = defaultdict(list)
            
            for exam in schedule:
                key = (exam.get('ders_id'), exam.get('tarih_saat'))
                exam_groups[key].append(exam)
            
            logger.info(f"📊 Schedule stats: {len(schedule)} total exams → {len(exam_groups)} unique course-time combinations")
            
            # Insert each unique exam (one record per course per time slot)
            success_count = 0
            error_count = 0
            
            for (ders_id, tarih_saat), exams in exam_groups.items():
                try:
                    sure = exams[0].get('sure', 120)
                    
                    # Calculate end time
                    if isinstance(tarih_saat, str):
                        tarih_saat = datetime.fromisoformat(tarih_saat)
                    
                    bitis_saat = tarih_saat + timedelta(minutes=sure)
                    
                    # Validate required fields
                    if not ders_id or not isinstance(ders_id, int):
                        logger.error(f"Invalid ders_id: {ders_id}")
                        error_count += 1
                        continue
                    
                    exam_data = {
                        'program_id': program_id,
                        'ders_id': ders_id,
                        'tarih': tarih_saat.date(),
                        'baslangic_saati': tarih_saat.time(),
                        'bitis_saati': bitis_saat.time()
                    }
                    
                    sinav_id = self.sinav_model.insert_sinav(exam_data)
                    
                    # Add all classroom assignments for this exam
                    for exam in exams:
                        derslik_id = exam.get('derslik_id')
                        if derslik_id and isinstance(derslik_id, int):
                            try:
                                self.sinav_model.assign_derslik(sinav_id, derslik_id)
                            except Exception as e:
                                logger.error(f"Error assigning classroom {derslik_id} to exam {sinav_id}: {e}")
                        else:
                            logger.warning(f"Invalid derslik_id for exam: {derslik_id}")
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error saving exam for ders_id {ders_id}: {e}", exc_info=True)
                    error_count += 1
            
            return {
                'success': True,
                'message': f"✅ {success_count} sınav kaydedildi! (Hata: {error_count})",
                'program_id': program_id,
                'success_count': success_count,
                'error_count': error_count
            }
            
        except Exception as e:
            logger.error(f"Error saving exam schedule: {e}")
            return {'success': False, 'message': str(e)}
    
    def validate_exam_schedule(self, schedule: List[Dict]) -> Dict:
        """Validate exam schedule for conflicts"""
        try:
            conflicts = []
            
            # Check for time conflicts
            for i, exam1 in enumerate(schedule):
                for j, exam2 in enumerate(schedule[i+1:], i+1):
                    # Same time, same classroom
                    if (exam1['tarih_saat'] == exam2['tarih_saat'] and
                        exam1.get('derslik_id') == exam2.get('derslik_id')):
                        conflicts.append({
                            'type': 'classroom_conflict',
                            'exam1': exam1['ders_kodu'],
                            'exam2': exam2['ders_kodu'],
                            'message': f"Aynı anda aynı derslik kullanılıyor"
                        })
            
            if conflicts:
                return {
                    'success': False,
                    'message': f"{len(conflicts)} çakışma tespit edildi!",
                    'conflicts': conflicts
                }
            
            return {
                'success': True,
                'message': "Program geçerli, çakışma yok!"
            }
            
        except Exception as e:
            logger.error(f"Error validating schedule: {e}")
            return {'success': False, 'message': str(e)}
