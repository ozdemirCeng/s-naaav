"""
Öğrenci (Student) Controller
Business logic for student management
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class OgrenciController:
    """Student business logic controller"""
    
    def __init__(self, ogrenci_model):
        self.ogrenci_model = ogrenci_model
    
    def create_ogrenci(self, ogrenci_data: Dict) -> Dict:
        """Create new student"""
        try:
            # Validate data
            if not ogrenci_data.get('ogrenci_no'):
                return {'success': False, 'message': "Öğrenci numarası gereklidir!"}
            
            if not ogrenci_data.get('ad_soyad'):
                return {'success': False, 'message': "Ad soyad gereklidir!"}
            
            # Check for duplicate
            existing = self.ogrenci_model.get_ogrenci_by_no(ogrenci_data['ogrenci_no'])
            
            if existing:
                return {
                    'success': False,
                    'message': f"Öğrenci no '{ogrenci_data['ogrenci_no']}' zaten mevcut!"
                }
            
            # Create student
            ogrenci_id = self.ogrenci_model.insert_ogrenci(ogrenci_data)
            
            return {
                'success': True,
                'message': f"Öğrenci başarıyla oluşturuldu!",
                'ogrenci_id': ogrenci_id
            }
            
        except Exception as e:
            logger.error(f"Error creating student: {e}")
            return {'success': False, 'message': str(e)}
    
    def update_ogrenci(self, ogrenci_no: str, ogrenci_data: Dict) -> Dict:
        """Update student"""
        try:
            self.ogrenci_model.update_ogrenci(ogrenci_no, ogrenci_data)
            
            return {
                'success': True,
                'message': f"Öğrenci başarıyla güncellendi!"
            }
            
        except Exception as e:
            logger.error(f"Error updating student: {e}")
            return {'success': False, 'message': str(e)}
    
    def delete_ogrenci(self, ogrenci_no: str) -> Dict:
        """Delete student"""
        try:
            self.ogrenci_model.delete_ogrenci(ogrenci_no)
            
            return {
                'success': True,
                'message': f"Öğrenci başarıyla silindi!"
            }
            
        except Exception as e:
            logger.error(f"Error deleting student: {e}")
            return {'success': False, 'message': str(e)}
    
    def bulk_import_students(self, students: List[Dict], bolum_id: int) -> Dict:
        """Bulk import students"""
        try:
            success_count = 0
            error_count = 0
            errors = []
            
            for student in students:
                student['bolum_id'] = bolum_id
                result = self.create_ogrenci(student)
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"{student['ogrenci_no']}: {result['message']}")
            
            return {
                'success': True,
                'message': f"{success_count} öğrenci başarıyla eklendi, {error_count} hata.",
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Error bulk importing students: {e}")
            return {'success': False, 'message': str(e)}
