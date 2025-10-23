"""
Oturma (Seating) Controller
Business logic for seating plan management
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class OturmaController:
    """Seating plan business logic controller"""
    
    def __init__(self, oturma_model, sinav_model):
        self.oturma_model = oturma_model
        self.sinav_model = sinav_model
    
    def save_seating_plan(self, sinav_id: int, plan: List[Dict]) -> Dict:
        """Save seating plan to database"""
        try:
            if not plan:
                return {'success': False, 'message': "Boş plan kaydedilemez!"}
            
            # Delete existing plan if any
            self.oturma_model.delete_by_sinav(sinav_id)
            
            # Insert new plan
            success_count = 0
            error_count = 0
            
            for oturma in plan:
                try:
                    oturma_data = {
                        'sinav_id': sinav_id,
                        'ogrenci_no': oturma['ogrenci_no'],
                        'derslik_id': oturma['derslik_id'],
                        'satir': oturma['satir'],
                        'sutun': oturma['sutun']
                    }
                    
                    self.oturma_model.insert_oturma(oturma_data)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error saving seating: {e}")
                    error_count += 1
            
            return {
                'success': True,
                'message': f"✅ {success_count} öğrenci oturma planına eklendi! (Hata: {error_count})",
                'success_count': success_count,
                'error_count': error_count
            }
            
        except Exception as e:
            logger.error(f"Error saving seating plan: {e}")
            return {'success': False, 'message': str(e)}
    
    def get_seating_plan(self, sinav_id: int) -> Dict:
        """Get seating plan for an exam"""
        try:
            plan = self.oturma_model.get_by_sinav(sinav_id)
            
            return {
                'success': True,
                'plan': plan,
                'count': len(plan)
            }
            
        except Exception as e:
            logger.error(f"Error getting seating plan: {e}")
            return {'success': False, 'message': str(e)}
