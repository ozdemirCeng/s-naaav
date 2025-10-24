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
        Generate seating plan for an exam across multiple classrooms
        
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
            sinav = self.sinav_model.get_sinav_by_id(sinav_id)
            if not sinav:
                raise Exception(f"Sınav bulunamadı: {sinav_id}")
            
            if progress_callback:
                progress_callback(20, "Öğrenciler yükleniyor...")
            
            # Get students enrolled in this course
            ogrenciler = self.ogrenci_model.get_ogrenciler_by_ders(sinav['ders_id'])
            if not ogrenciler:
                raise Exception(f"Bu derse kayıtlı öğrenci bulunamadı: {sinav['ders_kodu']}")
            
            # Shuffle students for randomized seating
            random.shuffle(ogrenciler)
            
            if progress_callback:
                progress_callback(30, "Derslik bilgileri yükleniyor...")
            
            # Get classroom assignments for this exam
            derslikler = self.sinav_model.get_sinav_derslikleri(sinav_id)
            if not derslikler:
                raise Exception(f"Bu sınav için derslik ataması bulunamadı!")
            
            logger.info(f"📊 Sınav: {sinav['ders_kodu']}, {len(ogrenciler)} öğrenci, {len(derslikler)} derslik")
            
            if progress_callback:
                progress_callback(50, "Oturma planı oluşturuluyor...")
            
            # Generate seating plan across all classrooms
            seating_plan = self._generate_multi_classroom_plan(
                ogrenciler, 
                derslikler,
                progress_callback
            )
            
            if progress_callback:
                progress_callback(100, "Tamamlandı!")
            
            logger.info(f"✅ Seating plan generated: {len(seating_plan)} öğrenci yerleştirildi")
            
            # Calculate statistics
            placed_count = len(seating_plan)
            unplaced_count = len(ogrenciler) - placed_count
            
            message = f"✅ {placed_count} öğrenci yerleştirildi"
            if unplaced_count > 0:
                message += f" (⚠️ {unplaced_count} öğrenci yerleştirilemedi - kapasite yetersiz)"
            
            return {
                'success': True,
                'message': message,
                'plan': seating_plan,
                'sinav': sinav,
                'derslikler': derslikler,
                'placed_count': placed_count,
                'unplaced_count': unplaced_count
            }
            
        except Exception as e:
            logger.error(f"Error generating seating plan: {e}", exc_info=True)
            return {
                'success': False,
                'message': f"Hata: {str(e)}",
                'plan': []
            }
    
    def _generate_multi_classroom_plan(
        self,
        students: List[Dict],
        derslikler: List[Dict],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[Dict]:
        """
        Generate seating plan across multiple classrooms with spacing
        
        Args:
            students: List of students to seat
            derslikler: List of classrooms
            progress_callback: Progress callback
            
        Returns:
            Complete seating plan
        """
        complete_plan = []
        student_index = 0
        total_students = len(students)
        
        # Sort classrooms by capacity (use largest first)
        sorted_derslikler = sorted(derslikler, key=lambda x: x['kapasite'], reverse=True)
        
        for idx, derslik in enumerate(sorted_derslikler):
            if student_index >= total_students:
                break
            
            if progress_callback:
                percent = 50 + int((idx / len(derslikler)) * 40)
                progress_callback(percent, f"Yerleştiriliyor: {derslik['derslik_adi']}")
            
            # Calculate how many students can fit with spacing (checkerboard pattern)
            satir_sayisi = derslik['satir_sayisi']
            sutun_sayisi = derslik['sutun_sayisi']
            
            # Checkerboard seating (skip adjacent seats)
            available_seats = []
            for satir in range(1, satir_sayisi + 1):
                for sutun in range(1, sutun_sayisi + 1):
                    # Checkerboard: (row + col) must be even
                    if (satir + sutun) % 2 == 0:
                        available_seats.append((satir, sutun))
            
            # Shuffle seats for randomization
            random.shuffle(available_seats)
            
            # Calculate how many students to place in this classroom
            remaining_students = total_students - student_index
            students_for_this_classroom = min(len(available_seats), remaining_students)
            
            logger.info(f"  📍 {derslik['derslik_adi']}: {students_for_this_classroom} öğrenci / {len(available_seats)} koltuk")
            
            # Assign students to seats
            for i in range(students_for_this_classroom):
                student = students[student_index]
                satir, sutun = available_seats[i]
                
                complete_plan.append({
                    'ogrenci_no': student['ogrenci_no'],
                    'ad_soyad': student['ad_soyad'],
                    'derslik_id': derslik['derslik_id'],
                    'derslik_kodu': derslik['derslik_kodu'],
                    'derslik_adi': derslik['derslik_adi'],
                    'satir': satir,
                    'sutun': sutun
                })
                
                student_index += 1
        
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
                    'message': f"Aynı koltuk ({assignment['derslik_adi']} - Sıra:{assignment['satir']}, Sütun:{assignment['sutun']}) iki öğrenciye atanmış"
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
