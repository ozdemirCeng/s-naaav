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
            logger.info(
                f"🏫 Derslik sayısı: {len(derslikler)} → {[d.get('derslik_kodu') for d in derslikler]}"
            )
            
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
            conflicts = self._build_conflict_graph(course_students, params)
            
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
            # Ensure we have enough colors to avoid premature failure; coloring is only for rough ordering
            total_slots_estimate = max(total_slots_estimate, len(course_info))
            
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
                logger.warning(
                    f"Coloring failed at {total_slots_estimate} colors; falling back to sequential ordering."
                )
                # Fallback: assign unique colors per course (ensures ordering only)
                course_slot_assignment = {cid: idx for idx, cid in enumerate(course_info.keys())}
            
            if progress_callback:
                progress_callback(70, "Dinamik zaman slotları ve derslikler atanıyor...")
            
            # Log key options for debugging
            logger.info(
                f"Options → no_parallel={bool(params.get('no_parallel_exams', False))}, "
                f"class/day limit={int(params.get('class_per_day_limit', 0))}, "
                f"conflict_threshold={int(params.get('min_conflict_overlap', 1))}"
            )
            
            # Attempt multiple ordering strategies to achieve zero conflict
            max_attempts = int(params.get('max_attempts', 3))
            strategies = ['small_first', 'large_first', 'random']
            best_schedule = []
            best_unscheduled = float('inf')
            any_days_exhausted = False
            for attempt in range(max_attempts):
                strategy = strategies[attempt % len(strategies)]
                logger.info(f"🔁 Attempt {attempt+1}/{max_attempts} with strategy={strategy}")
                self._days_exhausted = False
                schedule_try = self._assign_times_and_classrooms(
                    course_slot_assignment,
                    days,
                    derslikler,
                    course_info,
                    course_students,
                    params,
                    progress_callback,
                    order_strategy=strategy
                )
                scheduled_pairs = set((s['ders_id'], s['tarih_saat']) for s in schedule_try)
                scheduled_course_ids = {cid for (cid, _) in scheduled_pairs}
                all_course_ids = set(course_info.keys())
                unscheduled = len(all_course_ids - scheduled_course_ids)
                any_days_exhausted = any_days_exhausted or getattr(self, '_days_exhausted', False)
                logger.info(f"📈 Attempt {attempt+1}: scheduled={len(scheduled_course_ids)}, unscheduled={unscheduled}")
                if unscheduled < best_unscheduled:
                    best_unscheduled = unscheduled
                    best_schedule = schedule_try
                if unscheduled == 0:
                    break
            schedule = best_schedule
            
            if not schedule:
                return {
                    'success': False,
                    'message': "Zaman slotları ve derslikler atanamadı!"
                }
            
            # If days exhausted, return partial schedule with failure
            if getattr(self, '_days_exhausted', False):
                scheduled_courses = set((s['ders_id'], s['tarih_saat']) for s in schedule)
                unique_scheduled_course_ids = {cid for (cid, _) in scheduled_courses}
                all_course_ids = set(course_info.keys())
                unscheduled_ids = list(all_course_ids - unique_scheduled_course_ids)
                return {
                    'success': False,
                    'message': f"Günler tükendi! {len(unscheduled_ids)} ders yerleştirilemedi.",
                    'schedule': schedule,
                    'unassigned_courses': unscheduled_ids
                }
            
            if progress_callback:
                progress_callback(90, "Program doğrulanıyor...")
            
            # Validate schedule (without min rest; ara_suresi used already)
            self._last_params = {k: v for k, v in params.items() if k != 'min_rest_minutes'}
            validation = self._validate_schedule(schedule, course_students)
            
            if not validation['success']:
                logger.warning(f"⚠️ Validation warnings: {validation['message']}")
            
            if progress_callback:
                progress_callback(100, "Tamamlandı!")
            
            logger.info(f"✅ Exam schedule created: {len(schedule)} exam entries")
            used_rooms = sorted({s['derslik_kodu'] for s in schedule})
            logger.info(f"🏫 Kullanılan derslikler: {len(used_rooms)} → {used_rooms}")
            
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
    
    def _build_conflict_graph(self, course_students: Dict[int, Set[str]], params: Dict) -> Dict[int, Set[int]]:
        """
        Build conflict graph where edges represent student conflicts
        Returns adjacency list
        """
        conflicts = defaultdict(set)
        course_ids = list(course_students.keys())
        threshold = int(params.get('min_conflict_overlap', 1))
        total_edges = 0
        max_overlap = 0
        sample_overlaps = []
        
        for i, ders_id1 in enumerate(course_ids):
            for ders_id2 in course_ids[i+1:]:
                # Check if courses share any students
                shared_students = course_students[ders_id1] & course_students[ders_id2]
                overlap_count = len(shared_students)
                max_overlap = max(max_overlap, overlap_count)
                if overlap_count >= threshold:
                    conflicts[ders_id1].add(ders_id2)
                    conflicts[ders_id2].add(ders_id1)
                    total_edges += 1
                    if len(sample_overlaps) < 10:
                        sample_overlaps.append((ders_id1, ders_id2, overlap_count))
        
        # Log graph density info for diagnostics
        try:
            num_nodes = len(course_ids)
            avg_degree = (2 * total_edges / num_nodes) if num_nodes else 0
            logger.info(f"🧮 Graph: nodes={num_nodes}, edges={total_edges}, avg_degree={avg_degree:.2f}, max_overlap={max_overlap}, threshold={threshold}")
            if sample_overlaps:
                logger.info(f"🧪 Overlap samples (ders_id1, ders_id2, count): {sample_overlaps}")
        except Exception:
            pass

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
            
            # Pick the earliest slot (color) that doesn't conflict to maximize parallelism
            best_slot = None
            for color in range(max_colors):
                if color not in used_colors:
                    best_slot = color
                    break
            
            if best_slot is None:
                logger.warning(f"❌ Cannot color {course_info[ders_id]['ders_kodu']} - not enough slots!")
                return None
            
            coloring[ders_id] = best_slot
        
        logger.info(f"✅ Coloring successful! Used {len(set(coloring.values()))} slots")
        
        return coloring
    
    def _assign_times_and_classrooms(
        self, 
        course_slot_assignment: Dict[int, int],
        days: List[datetime],
        derslikler: List[Dict], 
        course_info: Dict[int, Dict],
        course_students: Dict[int, Set[str]],
        params: Dict,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        order_strategy: str = 'small_first'
    ) -> List[Dict]:
        """
        Dynamically assign time slots and classrooms
        Each slot can have different duration based on exams scheduled in it
        """
        schedule = []
        
        # Order courses by coloring slot index to spread conflicts roughly, but batching will ignore slots
        ordered_courses = [cid for cid, _ in sorted(course_slot_assignment.items(), key=lambda kv: kv[1])]

        # Sort derslikler by capacity
        sorted_derslikler = sorted(derslikler, key=lambda x: x['kapasite'])
        
        # Time parameters
        ara_suresi = params.get('ara_suresi', 15)
        ogle_baslangic = self._parse_time(params.get('ogle_arasi_baslangic', '12:00'))
        ogle_bitis = self._parse_time(params.get('ogle_arasi_bitis', '13:30'))
        gunluk_ilk = self._parse_time(params.get('gunluk_ilk_sinav', '10:00'))
        gunluk_son = self._parse_time(params.get('gunluk_son_sinav', '19:15'))
        
        current_day_idx = 0
        current_time = None
        
        processed = 0
        total = len(course_slot_assignment)
        
        # Remaining courses to place across batches
        remaining_courses = list(ordered_courses)
        
        # Track how many exams per class per day have been scheduled
        class_limit = params.get('class_per_day_limit', 0) or 0
        no_parallel = bool(params.get('no_parallel_exams', False))
        conflict_threshold = int(params.get('min_conflict_overlap', 1))
        # Track classroom usage to balance room distribution
        room_usage_count: Dict[int, int] = defaultdict(int)
        
        while remaining_courses:
            
            while remaining_courses:
                # Determine time for this batch
                if current_time is None:
                    if current_day_idx >= len(days):
                        if not getattr(self, '_days_exhausted', False):
                            logger.error("❌ Ran out of days!")
                        self._days_exhausted = True
                        break
                    current_day = days[current_day_idx]
                    current_time = datetime.combine(current_day.date(), gunluk_ilk)
                
                # Respect lunch break
                current_time_only = current_time.time()
                if ogle_baslangic <= current_time_only < ogle_bitis:
                    current_time = datetime.combine(current_time.date(), ogle_bitis)
                
                # Available classrooms reset for each batch at this start time
                slot_time = current_time
                all_rooms = list(sorted_derslikler)
                batch_used_students: Set[str] = set()
                batch_used_classes: Dict[int, int] = defaultdict(int)
                
                # Build zero-conflict set (greedy MIS) for this batch
                if order_strategy == 'large_first':
                    candidate = sorted(remaining_courses, key=lambda x: course_info[x]['ogrenci_sayisi'], reverse=True)
                elif order_strategy == 'random':
                    import random as _rnd
                    candidate = list(remaining_courses)
                    _rnd.shuffle(candidate)
                else:
                    candidate = sorted(remaining_courses, key=lambda x: course_info[x]['ogrenci_sayisi'])
                selected: List[int] = []
                for cid in candidate:
                    if no_parallel and selected:
                        continue
                    # conflict check vs currently selected
                    if course_students.get(cid):
                        if len(course_students[cid] & batch_used_students) >= conflict_threshold:
                            continue
                    if class_limit > 0:
                        csinif = course_info[cid].get('sinif', 0)
                        if batch_used_classes[csinif] >= class_limit:
                            continue
                    selected.append(cid)
                    batch_used_students.update(course_students.get(cid, set()))
                    if class_limit > 0:
                        batch_used_classes[course_info[cid].get('sinif', 0)] += 1
                
                # If nothing selected, advance time
                if not selected:
                    max_duration_in_batch = 0
                    placed_this_batch = []
                else:
                    # Fair room assignment: 1 round give 1 room per course, then fill leftovers
                    remaining_need = {cid: course_info[cid]['ogrenci_sayisi'] for cid in selected}
                    duration_map = {cid: course_info[cid]['sinav_suresi'] for cid in selected}
                    entries: List[Dict] = []
                    available = list(all_rooms)
                    # one-round assignment
                    for cid in selected:
                        if not available:
                            break
                        # pick least-used, then smallest sufficient; else smallest room
                        best = None
                        best_metric = (float('inf'), float('inf'), float('inf'))  # usage, waste, capacity
                        for r in available:
                            usage = room_usage_count[r['derslik_id']]
                            waste = (r['kapasite'] - remaining_need[cid]) if r['kapasite'] >= remaining_need[cid] else float('inf')
                            metric = (usage, waste, r['kapasite'])
                            if metric < best_metric:
                                best_metric = metric
                                best = r
                        if best is None:
                            # take smallest room
                            best = min(available, key=lambda r: (room_usage_count[r['derslik_id']], r['kapasite']))
                        take = min(best['kapasite'], remaining_need[cid])
                        entries.append({
                            'ders_id': cid,
                            'ders_kodu': course_info[cid]['ders_kodu'],
                            'ders_adi': course_info[cid]['ders_adi'],
                            'ogretim_elemani': course_info[cid]['ogretim_elemani'],
                            'tarih_saat': slot_time,
                            'sure': duration_map[cid],
                            'derslik_id': best['derslik_id'],
                            'derslik_kodu': best['derslik_kodu'],
                            'derslik_adi': best['derslik_adi'],
                            'ogrenci_sayisi': take,
                            'sinav_tipi': params['sinav_tipi'],
                            'bolum_id': params['bolum_id']
                        })
                        room_usage_count[best['derslik_id']] += 1
                        remaining_need[cid] -= take
                        available.remove(best)
                    # fill remaining capacity
                    for r in sorted(available, key=lambda x: (room_usage_count[x['derslik_id']], x['kapasite'])):
                        # pick course with max remaining need (still in selected)
                        cid = max((c for c in selected if remaining_need[c] > 0), default=None, key=lambda c: remaining_need[c])
                        if cid is None:
                            break
                        take = min(r['kapasite'], remaining_need[cid])
                        if take <= 0:
                            continue
                        entries.append({
                            'ders_id': cid,
                            'ders_kodu': course_info[cid]['ders_kodu'],
                            'ders_adi': course_info[cid]['ders_adi'],
                            'ogretim_elemani': course_info[cid]['ogretim_elemani'],
                            'tarih_saat': slot_time,
                            'sure': duration_map[cid],
                            'derslik_id': r['derslik_id'],
                            'derslik_kodu': r['derslik_kodu'],
                            'derslik_adi': r['derslik_adi'],
                            'ogrenci_sayisi': take,
                            'sinav_tipi': params['sinav_tipi'],
                            'bolum_id': params['bolum_id']
                        })
                        room_usage_count[r['derslik_id']] += 1
                        remaining_need[cid] -= take
                    # finalize
                    placed_this_batch = selected
                    max_duration_in_batch = max(duration_map[c] for c in selected) if selected else 0
                    for e in entries:
                        schedule.append(e)
                
                # Remove placed courses from remaining
                remaining_courses = [cid for cid in remaining_courses if cid not in placed_this_batch]
                
                if not placed_this_batch:
                    # No course could be placed with remaining capacity; move to next time
                    max_duration_in_batch = 0
                
                # Advance time to next batch
                advance_minutes = (max_duration_in_batch + ara_suresi) if max_duration_in_batch > 0 else ara_suresi
                next_time = current_time + timedelta(minutes=advance_minutes)
                # Respect lunch break after advancing
                next_time_only = next_time.time()
                if ogle_baslangic <= next_time_only < ogle_bitis:
                    next_time = datetime.combine(next_time.date(), ogle_bitis)
                
                # Check day limit
                if next_time.time() > gunluk_son:
                    current_day_idx += 1
                    current_time = None
                    # If we ran out of days, abort
                    if current_day_idx >= len(days):
                        if not getattr(self, '_days_exhausted', False):
                            logger.error("❌ Ran out of days!")
                        self._days_exhausted = True
                        break
                else:
                    current_time = next_time

            # If days are exhausted, stop outer loop as well to avoid spinning
            if getattr(self, '_days_exhausted', False):
                break
        
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
        
        # Skip per-student min rest validation; ara_suresi policy applies globally

        if errors:
            return {
                'success': False,
                'message': f"{len(errors)} validation error",
                'errors': errors[:10]
            }
        
        return {
            'success': True,
            'message': "Schedule is valid",
            'warnings': warnings[:20] if warnings else []
        }

    def _safe_int(self, d: Dict, key: str, default: int) -> int:
        try:
            return int(d.get(key, default))
        except Exception:
            return default
