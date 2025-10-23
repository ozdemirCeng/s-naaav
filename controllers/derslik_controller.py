"""
Derslik (Classroom) Controller
Business logic for classroom management
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DerslikController:
    """Classroom business logic controller"""
    
    def __init__(self, derslik_model):
        self.derslik_model = derslik_model
    
    def create_derslik(self, derslik_data: Dict) -> Dict:
        """Create new classroom"""
        try:
            # Validate data
            is_valid, message = self.derslik_model.validate_derslik_data(derslik_data)
            if not is_valid:
                return {'success': False, 'message': message}
            
            # Check for duplicate
            existing = self.derslik_model.get_derslik_by_kod(
                derslik_data['bolum_id'],
                derslik_data['derslik_kodu']
            )
            
            if existing:
                return {
                    'success': False,
                    'message': f"Derslik kodu '{derslik_data['derslik_kodu']}' zaten mevcut!"
                }
            
            # Create classroom
            derslik_id = self.derslik_model.insert_derslik(derslik_data)
            
            return {
                'success': True,
                'message': f"Derslik başarıyla oluşturuldu!",
                'derslik_id': derslik_id
            }
            
        except Exception as e:
            logger.error(f"Error creating classroom: {e}")
            return {'success': False, 'message': str(e)}
    
    def update_derslik(self, derslik_id: int, derslik_data: Dict) -> Dict:
        """Update classroom"""
        try:
            # Validate data
            is_valid, message = self.derslik_model.validate_derslik_data(derslik_data)
            if not is_valid:
                return {'success': False, 'message': message}
            
            # Update classroom
            self.derslik_model.update_derslik(derslik_id, derslik_data)
            
            return {
                'success': True,
                'message': f"Derslik başarıyla güncellendi!"
            }
            
        except Exception as e:
            logger.error(f"Error updating classroom: {e}")
            return {'success': False, 'message': str(e)}
    
    def delete_derslik(self, derslik_id: int) -> Dict:
        """Delete classroom (soft delete)"""
        try:
            # Check if classroom is in use
            usage = self.derslik_model.check_derslik_kullanimi(derslik_id)
            
            if usage['sinav_sayisi'] > 0:
                return {
                    'success': False,
                    'message': f"Bu derslik {usage['sinav_sayisi']} sınavda kullanılıyor. Önce sınavları silin."
                }
            
            # Delete classroom
            self.derslik_model.delete_derslik(derslik_id)
            
            return {
                'success': True,
                'message': f"Derslik başarıyla silindi!"
            }
            
        except Exception as e:
            logger.error(f"Error deleting classroom: {e}")
            return {'success': False, 'message': str(e)}
    
    def get_derslik_statistics(self, bolum_id: int) -> Dict:
        """Get classroom statistics"""
        try:
            derslikler = self.derslik_model.get_derslikler_by_bolum(bolum_id)
            
            total_capacity = sum(d['kapasite'] for d in derslikler)
            avg_capacity = total_capacity / len(derslikler) if derslikler else 0
            
            return {
                'success': True,
                'statistics': {
                    'total_derslikler': len(derslikler),
                    'total_capacity': total_capacity,
                    'avg_capacity': round(avg_capacity, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'success': False, 'message': str(e)}
