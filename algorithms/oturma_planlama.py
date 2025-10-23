"""
Oturma Planı Algoritması
Intelligent seating plan generation with spacing optimization
"""

import logging
import random
from typing import Dict, List, Callable, Optional
from models.database import db
from models.ogrenci_model import OgrenciModel
from models.derslik_model import DerslikModel
from models.sinav_model import SinavModel

logger = logging.getLogger(__name__)


class OturmaPlanlama:
    """Seating plan generation algorithm"""
    
    def __init__(self):
        self.ogrenci_model = OgrenciModel(db)
        self.derslik_model = DerslikModel(db)
        self.sinav_model = SinavModel(db)
    
    def generate_seating_plan(
        self,
        sinav_id: int,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict:
        """
        Generate seating plan for an exam
        
        Args:
            sinav_id: Exam ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with success status and seating plan
        """
        try:
            if progress_callback:
                progress_callback(10, "Sınav bilgileri yükleniyor...")
            
            # Get exam details
            # Note: You'll need to implement get_sinav_by_id in SinavModel
            # For now, we'll work with what we have
            
            if progress_callback:
                progress_callback(20, "Öğrenciler yükleniyor...")
            
            # Get students for this course
            # Note: This requires ders_kayitlari table or similar
            # For demo, we'll get all students from the department
            # In production, filter by course enrollment
            
            if progress_callback:
                progress_callback(30, "Derslik bilgileri yükleniyor...")
            
            # Get classroom assignments for this exam
            # Note: Need to implement this based on your database schema
            
            if progress_callback:
                progress_callback(50, "Oturma planı oluşturuluyor...")
            
            # Generate seating plan
            # This is a simplified version - expand with your business logic
            seating_plan = self._generate_simple_plan(sinav_id)
            
            if progress_callback:
                progress_callback(100, "Tamamlandı!")
            
            logger.info(f"✅ Seating plan generated for exam {sinav_id}")
            
            return {
                'success': True,
                'message': f"{len(seating_plan)} öğrenci yerleştirildi",
                'plan': seating_plan
            }
            
        except Exception as e:
            logger.error(f"Seating plan generation error: {e}")
            return {
                'success': False,
                'message': f"Plan oluşturma hatası: {str(e)}"
            }
    
    def _generate_simple_plan(self, sinav_id: int) -> List[Dict]:
        """
        Generate a simple seating plan
        
        This is a placeholder implementation.
        In production, implement:
        - Spacing rules (skip seats, alternating rows)
        - Multiple classroom assignments
        - Student grouping by class/department
        - Randomization to prevent cheating
        """
        # TODO: Implement actual seating algorithm
        # For now, return empty list as placeholder
        
        return []
    
    def distribute_students_in_classroom(
        self,
        students: List[Dict],
        derslik: Dict,
        spacing: int = 2
    ) -> List[Dict]:
        """
        Distribute students in a classroom with spacing
        
        Args:
            students: List of students to seat
            derslik: Classroom information
            spacing: Seats to skip between students
            
        Returns:
            List of seating assignments
        """
        seating = []
        satir_sayisi = derslik['satir_sayisi']
        sutun_sayisi = derslik['sutun_sayisi']
        
        # Create seating grid
        available_seats = []
        for satir in range(1, satir_sayisi + 1):
            for sutun in range(1, sutun_sayisi + 1):
                # Apply spacing rule (e.g., skip every other seat)
                if spacing == 1 or (satir + sutun) % spacing == 0:
                    available_seats.append((satir, sutun))
        
        # Shuffle for randomization
        random.shuffle(available_seats)
        
        # Assign students to seats
        for i, student in enumerate(students):
            if i >= len(available_seats):
                logger.warning(f"Not enough seats for all students in {derslik['derslik_kodu']}")
                break
            
            satir, sutun = available_seats[i]
            
            seating.append({
                'ogrenci_no': student['ogrenci_no'],
                'ad_soyad': student['ad_soyad'],
                'derslik_id': derslik['derslik_id'],
                'derslik_kodu': derslik['derslik_kodu'],
                'satir': satir,
                'sutun': sutun
            })
        
        return seating
    
    def optimize_multi_classroom_seating(
        self,
        students: List[Dict],
        derslikler: List[Dict],
        spacing: int = 2
    ) -> List[Dict]:
        """
        Optimize seating across multiple classrooms
        
        Args:
            students: List of students
            derslikler: List of available classrooms
            spacing: Spacing rule
            
        Returns:
            Complete seating plan across all classrooms
        """
        # Sort classrooms by capacity (descending)
        sorted_derslikler = sorted(derslikler, key=lambda x: x['kapasite'], reverse=True)
        
        # Shuffle students for randomization
        shuffled_students = students.copy()
        random.shuffle(shuffled_students)
        
        complete_plan = []
        student_index = 0
        
        for derslik in sorted_derslikler:
            # Calculate capacity with spacing
            effective_capacity = derslik['kapasite'] // spacing
            
            # Get students for this classroom
            classroom_students = shuffled_students[student_index:student_index + effective_capacity]
            
            if not classroom_students:
                break
            
            # Generate seating for this classroom
            classroom_seating = self.distribute_students_in_classroom(
                classroom_students,
                derslik,
                spacing
            )
            
            complete_plan.extend(classroom_seating)
            student_index += len(classroom_students)
            
            if student_index >= len(shuffled_students):
                break
        
        return complete_plan
    
    def validate_seating_plan(self, plan: List[Dict]) -> Dict:
        """Validate seating plan for conflicts"""
        conflicts = []
        
        # Check for duplicate seat assignments
        seat_map = {}
        for assignment in plan:
            key = f"{assignment['derslik_id']}_{assignment['satir']}_{assignment['sutun']}"
            
            if key in seat_map:
                conflicts.append({
                    'type': 'duplicate_seat',
                    'student1': seat_map[key],
                    'student2': assignment['ogrenci_no'],
                    'message': 'Aynı koltuk iki öğrenciye atanmış'
                })
            else:
                seat_map[key] = assignment['ogrenci_no']
        
        if conflicts:
            return {
                'success': False,
                'conflicts': conflicts,
                'message': f"{len(conflicts)} çakışma bulundu"
            }
        
        return {
            'success': True,
            'message': "Plan geçerli"
        }
