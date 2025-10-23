"""
Sınav (Exam) Controller
Business logic for exam schedule management
"""

import logging
from typing import Dict, List
from datetime import datetime

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
            
            # First, create a program
            program_data = {
                'bolum_id': schedule[0].get('bolum_id'),
                'program_adi': f"Sınav Programı - {datetime.now().strftime('%d.%m.%Y')}",
                'sinav_tipi': schedule[0].get('sinav_tipi', 'Final'),
                'aktif': True
            }
            
            program_result = self.create_exam_program(program_data)
            
            if not program_result['success']:
                return program_result
            
            program_id = program_result['program_id']
            
            # Insert each exam
            success_count = 0
            error_count = 0
            
            for exam in schedule:
                try:
                    exam_data = {
                        'program_id': program_id,
                        'ders_id': exam.get('ders_id'),
                        'tarih_saat': exam.get('tarih_saat'),
                        'sure': exam.get('sure', 120)
                    }
                    
                    sinav_id = self.sinav_model.insert_sinav(exam_data)
                    
                    # Add classroom assignment
                    if exam.get('derslik_id'):
                        self.sinav_model.assign_derslik(sinav_id, exam['derslik_id'])
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error saving exam: {e}")
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
