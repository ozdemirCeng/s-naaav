"""
Sınav Planlama Algoritması
Graph Coloring based intelligent exam scheduling with constraint satisfaction
Dynamic time slot allocation based on exam duration
"""

import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Callable, Optional, Set, Tuple
from collections import defaultdict
from models.database import db
from models.ders_model import DersModel
from models.derslik_model import DerslikModel
from models.ogrenci_model import OgrenciModel

logger = logging.getLogger(__name__)


class SinavPlanlama:
    """Exam scheduling algorithm using graph coloring approach"""
    
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
        Create exam schedule using graph coloring approach with dynamic time slots
        
        Args:
            params: Scheduling parameters
                - bolum_id: Department ID
                - sinav_tipi: Exam type (Vize/Final/Bütünleme)
                - baslangic_tarih: Start date
                - bitis_tarih: End date
                - varsayilan_sinav_suresi: Default exam duration (minutes)
                - ara_suresi: Break duration (minutes)
                - ders_sinavlari_suresi: Dict[ders_id, duration] - Custom durations
                - ogle_arasi_baslangic: Lunch break start time (default: "12:00")
                - ogle_arasi_bitis: Lunch break end time (default: "13:30")
                - gunluk_ilk_sinav: First exam time (default: "10:00")
                - gunluk_son_sinav: Last exam start time (default: "19:15")
            progress_callback: Optional callback for progress updates
                
        Returns:
            Dictionary with success status and schedule data
        """
        try:
            if progress_callback:
                progress_callback(5, "Dersler yükleniyor...")
            
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
                progress_callback(10, "Derslikler yükleniyor...")
            
            # Get available classrooms
            derslikler = self.derslik_model.get_derslikler_by_bolum(params['bolum_id'])
            
            if not derslikler:
                return {
                    'success': False,
                    'message': "Derslik bulunamadı!"
                }
            
            if progress_callback:
                progress_callback(15, "Öğrenci kayıtları analiz ediliyor...")
            
            # Build course-student mapping and conflict graph
            course_students = {}
            course_info = {}
            
            # Get custom exam durations
            ders_sinavlari_suresi = params.get('ders_sinavlari_suresi', {})
            varsayilan_sure = params.get('varsayilan_sinav_suresi', 75)
            
            for ders in dersler:
                ogrenciler = self.ogrenci_model.get_ogrenciler_by_ders(ders['ders_id'])
                student_ids = set(o['ogrenci_no'] for o in ogrenciler)
                
                # Get exam duration for this course (custom or default)
                sinav_suresi = ders_sinavlari_suresi.get(ders['ders_id'], varsayilan_sure)
                
                course_students[ders['ders_id']] = student_ids
                course_info[ders['ders_id']] = {
                    'ders_kodu': ders['ders_kodu'],
                    'ders_adi': ders['ders_adi'],
                    'ogretim_elemani': ders.get('ogretim_elemani', ''),
                    'sinif': ders.get('sinif', 1),
                    'ogrenci_sayisi': len(student_ids),
                    'sinav_suresi': sinav_suresi  # Each course has its own duration
                }
            
            if progress_callback:
                progress_callback(25, "Ders çakışma grafiği oluşturuluyor...")
            
            # Build conflict graph (adjacency list)
            conflicts = self._build_conflict_graph(course_students)
            
            logger.info(f"📊 Conflict graph: {len(conflicts)} courses with conflicts")
            
            if progress_callback:
                progress_callback(35, "Günlük sınav kapasitesi hesaplanıyor...")
            
            # Calculate how many exam slots we can fit per day (dynamically)
            # This is approximate - actual slots will be calculated dynamically
            ara_suresi = params.get('ara_suresi', 15)
            avg_slot_duration = varsayilan_sure + ara_suresi
            
            # Time constraints
            ogle_baslangic = self._parse_time(params.get('ogle_arasi_baslangic', '12:00'))
            ogle_bitis = self._parse_time(params.get('ogle_arasi_bitis', '13:30'))
            gunluk_ilk = self._parse_time(params.get('gunluk_ilk_sinav', '10:00'))
            gunluk_son = self._parse_time(params.get('gunluk_son_sinav', '19:15'))
            
            # Calculate available minutes per day
            total_minutes = (gunluk_son.hour * 60 + gunluk_son.minute) - (gunluk_ilk.hour * 60 + gunluk_ilk.minute)
            lunch_minutes = (ogle_bitis.hour * 60 + ogle_bitis.minute) - (ogle_baslangic.hour * 60 + ogle_baslangic.minute)
            available_minutes = total_minutes - lunch_minutes
            
            # Approximate slots per day
            approx_slots_per_day = available_minutes // avg_slot_duration
            
            # Generate available days
            allowed_weekdays = params.get('allowed_weekdays', [0, 1, 2, 3, 4])
            days = self._generate_exam_days(
                params['baslangic_tarih'],
                params['bitis_tarih'],
                allowed_weekdays
            )
            
            # Estimate total available slots (colors for graph coloring)
            total_slots_estimate = len(days) * approx_slots_per_day
            
            logger.info(f"📅 {len(days)} days available")
            logger.info(f"⏰ ~{approx_slots_per_day} slots per day, ~{total_slots_estimate} total")
            
            if progress_callback:
                progress_callback(45, "Dersler slotlara yerleştiriliyor (Graph Coloring)...")
            
            # Graph coloring with greedy heuristics
            course_slot_assignment = self._graph_coloring(
                list(course_info.keys()),
                conflicts,
                course_info,
                total_slots_estimate,
                progress_callback
            )
            
            if not course_slot_assignment:
                return {
                    'success': False,
                    'message': f"Dersler {total_slots_estimate} slot'a sığdırılamadı! Daha fazla gün ekleyin veya ders sayısını azaltın."
                }
            
            if progress_callback:
                progress_callback(70, "Dinamik zaman slotları ve derslikler atanıyor...")
            
            # Dynamically assign time slots and classrooms
            schedule = self._assign_times_and_classrooms(
                course_slot_assignment,
                days,
                derslikler,
                course_info,
                params,
                progress_callback
            )
            
            if not schedule:
                return {
                    'success': False,
                    'message': "Zaman slotları ve derslikler atanamadı!"
                }
            
            if progress_callback:
                progress_callback(90, "Program doğrulanıyor...")
            
            # Validate schedule
            validation = self._validate_schedule(schedule, course_students)
            
            if not validation['success']:
                logger.warning(f"⚠️ Validation warnings: {validation['message']}")
            
            if progress_callback:
                progress_callback(100, "Tamamlandı!")
            
            logger.info(f"✅ Exam schedule created: {len(schedule)} exam entries")
            
            # Count unique exams (grouped by course + time)
            unique_exams = set((s['ders_id'], s['tarih_saat']) for s in schedule)
            logger.info(f"📝 {len(unique_exams)} unique exams scheduled")
            
            return {
                'success': True,
                'message': f"✅ {len(unique_exams)} sınav başarıyla programlandı!",
                'schedule': schedule,
                'stats': {
                    'total_courses': len(dersler),
                    'scheduled_courses': len(unique_exams),
                    'days_used': len(set(s['tarih_saat'].date() for s in schedule))
                }
            }
            
        except Exception as e:
            logger.error(f"Exam scheduling error: {e}", exc_info=True)
            return {
                'success': False,
                'message': f"Program oluşturma hatası: {str(e)}"
            }
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string HH:MM to time object"""
        parts = time_str.split(':')
        return time(hour=int(parts[0]), minute=int(parts[1]))
    
    def _generate_exam_days(
        self,
        start_date: datetime,
        end_date: datetime,
        allowed_weekdays: List[int]
    ) -> List[datetime]:
        """Generate list of available exam days"""
        days = []
        current = start_date
        
        while current <= end_date:
            if current.weekday() in allowed_weekdays:
                days.append(current)
            current += timedelta(days=1)
        
        return days
    
    def _build_conflict_graph(self, course_students: Dict[int, Set[str]]) -> Dict[int, Set[int]]:
        """
        Build conflict graph where edges represent student conflicts
        Returns adjacency list
        """
        conflicts = defaultdict(set)
        course_ids = list(course_students.keys())
        
        for i, ders_id1 in enumerate(course_ids):
            for ders_id2 in course_ids[i+1:]:
                # Check if courses share any students
                shared_students = course_students[ders_id1] & course_students[ders_id2]
                
                if shared_students:
                    conflicts[ders_id1].add(ders_id2)
                    conflicts[ders_id2].add(ders_id1)
        
        return conflicts
    
    def _graph_coloring(
        self,
        courses: List[int],
        conflicts: Dict[int, Set[int]],
        course_info: Dict[int, Dict],
        max_colors: int,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Optional[Dict[int, int]]:
        """
        Graph coloring using Welsh-Powell greedy algorithm
        
        Returns:
            Dict mapping course_id -> slot_index, or None if impossible
        """
        # Calculate degree (number of conflicts) for each course
        degrees = {ders_id: len(conflicts.get(ders_id, set())) for ders_id in courses}
        
        # Sort by degree (descending), then by student count (descending)
        sorted_courses = sorted(
            courses,
            key=lambda x: (
                -degrees[x],  # More conflicts first (priority)
                course_info[x]['ogrenci_sayisi'],  # SMALLER classes first (easier to fit)
                course_info[x]['sinif']  # Lower classes first
            )
        )
        
        logger.info(f"🎨 Starting graph coloring for {len(courses)} courses")
        logger.info(f"📊 Max degree: {max(degrees.values()) if degrees else 0}")
        
        # Color assignment
        coloring = {}
        
        # Track which courses are in each slot (for same-class spreading)
        slot_classes = defaultdict(set)
        
        for idx, ders_id in enumerate(sorted_courses):
            if progress_callback and idx % 5 == 0:
                percent = 45 + int((idx / len(courses)) * 25)
                progress_callback(percent, f"Yerleştiriliyor: {course_info[ders_id]['ders_kodu']}")
            
            # Find available colors (slots)
            used_colors = set()
            
            # Colors used by conflicting courses
            for neighbor_id in conflicts.get(ders_id, set()):
                if neighbor_id in coloring:
                    used_colors.add(coloring[neighbor_id])
            
            # Try to find a color that doesn't conflict and preferably doesn't have same class
            sinif = course_info[ders_id]['sinif']
            
            # First try: Find slot without conflicts and without same class
            best_slot = None
            for color in range(max_colors):
                if color not in used_colors:
                    if sinif not in slot_classes[color]:
                        best_slot = color
                        break
            
            # Second try: Any slot without conflicts
            if best_slot is None:
                for color in range(max_colors):
                    if color not in used_colors:
                        best_slot = color
                        break
            
            if best_slot is None:
                logger.warning(f"❌ Cannot color {course_info[ders_id]['ders_kodu']} - not enough slots!")
                return None
            
            coloring[ders_id] = best_slot
            slot_classes[best_slot].add(sinif)
        
        logger.info(f"✅ Coloring successful! Used {len(set(coloring.values()))} slots")
        
        return coloring
    
    def _assign_times_and_classrooms(
        self, 
        course_slot_assignment: Dict[int, int],
        days: List[datetime],
        derslikler: List[Dict], 
        course_info: Dict[int, Dict],
        params: Dict,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[Dict]:
        """
        Dynamically assign time slots and classrooms
        Each slot can have different duration based on exams scheduled in it
        """
        schedule = []
        
        # Group courses by slot index
        slot_courses = defaultdict(list)
        for ders_id, slot_idx in course_slot_assignment.items():
            slot_courses[slot_idx].append(ders_id)
        
        # Sort derslikler by capacity
        sorted_derslikler = sorted(derslikler, key=lambda x: x['kapasite'])
        
        # Time parameters
        ara_suresi = params.get('ara_suresi', 15)
        ogle_baslangic = self._parse_time(params.get('ogle_arasi_baslangic', '12:00'))
        ogle_bitis = self._parse_time(params.get('ogle_arasi_bitis', '13:30'))
        gunluk_ilk = self._parse_time(params.get('gunluk_ilk_sinav', '10:00'))
        gunluk_son = self._parse_time(params.get('gunluk_son_sinav', '19:15'))
        
        # Assign slots to actual times dynamically
        sorted_slot_indices = sorted(slot_courses.keys())
        
        current_day_idx = 0
        current_time = None
        
        processed = 0
        total = len(course_slot_assignment)
        
        for slot_idx in sorted_slot_indices:
            course_ids = slot_courses[slot_idx]
            
            # Determine time for this slot
            if current_time is None:
                # Start of first day
                if current_day_idx >= len(days):
                    logger.error("❌ Ran out of days!")
                    break
                
                current_day = days[current_day_idx]
                current_time = datetime.combine(current_day.date(), gunluk_ilk)
            
            # Check if we need to move to next day
            # Calculate longest exam in this slot
            max_duration = max(course_info[cid]['sinav_suresi'] for cid in course_ids)
            exam_end_time = current_time + timedelta(minutes=max_duration)
            
            # Check if exam would end after last allowed time
            max_allowed_end = datetime.combine(current_time.date(), gunluk_son) + timedelta(minutes=max_duration)
            
            if exam_end_time > max_allowed_end:
                # Move to next day
                current_day_idx += 1
                if current_day_idx >= len(days):
                    logger.error("❌ Ran out of days!")
                    break
                
                current_day = days[current_day_idx]
                current_time = datetime.combine(current_day.date(), gunluk_ilk)
            
            # Check if we're in lunch break
            current_time_only = current_time.time()
            if ogle_baslangic <= current_time_only < ogle_bitis:
                # Skip to after lunch
                current_time = datetime.combine(current_time.date(), ogle_bitis)
            
            # Assign classrooms for courses in this slot
            slot_time = current_time
            available_derslikler = list(sorted_derslikler)  # Copy
            
            # Sort courses by student count (SMALLER first for better packing)
            course_ids_sorted = sorted(
                course_ids,
                key=lambda x: course_info[x]['ogrenci_sayisi']
            )
            
            for ders_id in course_ids_sorted:
                processed += 1
                
                if progress_callback and processed % 3 == 0:
                    percent = 70 + int((processed / total) * 20)
                    progress_callback(percent, f"Atanıyor: {course_info[ders_id]['ders_kodu']}")
                
                ogrenci_sayisi = course_info[ders_id]['ogrenci_sayisi']
                sinav_suresi = course_info[ders_id]['sinav_suresi']
                
                # BEST FIT classroom selection strategy
                classrooms_used = []
                remaining_students = ogrenci_sayisi
                
                # Try single classroom first - use BEST FIT (smallest that works)
                best_fit_derslik = None
                min_waste = float('inf')
                
                for derslik in available_derslikler:
                    if derslik['kapasite'] >= ogrenci_sayisi:
                        waste = derslik['kapasite'] - ogrenci_sayisi
                        if waste < min_waste:
                            min_waste = waste
                            best_fit_derslik = derslik
                
                if best_fit_derslik:
                    classrooms_used = [best_fit_derslik]
                    remaining_students = 0
                    available_derslikler.remove(best_fit_derslik)
                    logger.debug(f"Best fit: {course_info[ders_id]['ders_kodu']} → {best_fit_derslik['derslik_kodu']} (waste: {min_waste})")
                
                # If no single classroom fits, use multiple SMALLEST first
                if remaining_students > 0:
                    classrooms_used = []
                    # Use SMALLEST classrooms first - saves big ones for large single exams
                    available_sorted = sorted(available_derslikler, key=lambda x: x['kapasite'])
                    
                    for derslik in available_sorted:
                        if remaining_students <= 0:
                            break
                        
                        classrooms_used.append(derslik)
                        remaining_students -= derslik['kapasite']
                        available_derslikler.remove(derslik)
                
                if remaining_students > 0:
                    logger.error(f"❌ Not enough classroom capacity for {course_info[ders_id]['ders_kodu']}")
                    continue
                
                # Create exam entries
                for derslik in classrooms_used:
                    students_in_room = min(derslik['kapasite'], ogrenci_sayisi)
                    
                    exam = {
                        'ders_id': ders_id,
                        'ders_kodu': course_info[ders_id]['ders_kodu'],
                        'ders_adi': course_info[ders_id]['ders_adi'],
                        'ogretim_elemani': course_info[ders_id]['ogretim_elemani'],
                        'tarih_saat': slot_time,
                        'sure': sinav_suresi,  # Each course's own duration
                        'derslik_id': derslik['derslik_id'],
                        'derslik_kodu': derslik['derslik_kodu'],
                        'derslik_adi': derslik['derslik_adi'],
                        'ogrenci_sayisi': students_in_room,
                        'sinav_tipi': params['sinav_tipi'],
                        'bolum_id': params['bolum_id']
                    }
                    
                    schedule.append(exam)
                    ogrenci_sayisi -= students_in_room
                
                if len(classrooms_used) > 1:
                    logger.info(f"📍 {course_info[ders_id]['ders_kodu']}: {len(classrooms_used)} derslik")
            
            # Move current_time forward for next slot
            # Use the longest exam duration in this slot + break
            max_duration = max(course_info[cid]['sinav_suresi'] for cid in course_ids)
            next_time = current_time + timedelta(minutes=max_duration + ara_suresi)
            
            # Check if next time falls in lunch break
            next_time_only = next_time.time()
            if ogle_baslangic <= next_time_only < ogle_bitis:
                # Skip to after lunch
                next_time = datetime.combine(next_time.date(), ogle_bitis)
            
            # Check if next time exceeds daily limit
            if next_time.time() > gunluk_son:
                # Move to next day
                current_day_idx += 1
                current_time = None
            else:
                current_time = next_time
        
        return schedule
    
    def _validate_schedule(self, schedule: List[Dict], course_students: Dict[int, Set[str]]) -> Dict:
        """Validate exam schedule for conflicts"""
        errors = []
        warnings = []
        
        # Group by time slot
        slots = defaultdict(list)
        for exam in schedule:
            slot_key = exam['tarih_saat'].isoformat() if isinstance(exam['tarih_saat'], datetime) else exam['tarih_saat']
            slots[slot_key].append(exam)
        
        # Check each slot
        for slot_key, exams in slots.items():
            # Check classroom conflicts
            derslikler_in_slot = [e['derslik_id'] for e in exams]
            if len(derslikler_in_slot) != len(set(derslikler_in_slot)):
                errors.append(f"Slot {slot_key}: Aynı derslik birden fazla kullanılmış!")
            
            # Check student conflicts
            students_in_slot = set()
            for exam in exams:
                ders_id = exam['ders_id']
                students = course_students.get(ders_id, set())
                
                overlap = students_in_slot & students
                if overlap:
                    errors.append(f"Slot {slot_key}: {len(overlap)} öğrenci çakışması!")
                
                students_in_slot.update(students)
        
        if errors:
            return {
                'success': False,
                'message': f"{len(errors)} validation error",
                'errors': errors[:10]
            }
        
        return {
            'success': True,
            'message': "Schedule is valid"
        }
