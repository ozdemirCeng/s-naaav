"""
Sınav Planlama Algoritması
Graph Coloring based intelligent exam scheduling with constraint satisfaction
Dynamic time slot allocation based on exam duration
"""

import logging
import random
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
                    'message': "❌ Derslik bulunamadı! Lütfen önce derslik tanımlayın."
                }
            
            # Calculate total classroom capacity
            total_capacity = sum(d['kapasite'] for d in derslikler)
            logger.info(f"📊 Toplam derslik kapasitesi: {total_capacity} kişi")
            
            if progress_callback:
                progress_callback(15, "Öğrenci kayıtları analiz ediliyor...")
            
            # Build course-student mapping and conflict graph
            course_students = {}
            course_info = {}
            
            # Get custom exam durations
            ders_sinavlari_suresi = params.get('ders_sinavlari_suresi', {})
            varsayilan_sure = params.get('varsayilan_sinav_suresi', 75)
            
            # Check for capacity issues
            capacity_errors = []
            
            for ders in dersler:
                ogrenciler = self.ogrenci_model.get_ogrenciler_by_ders(ders['ders_id'])
                student_ids = set(o['ogrenci_no'] for o in ogrenciler)
                ogrenci_sayisi = len(student_ids)
                
                # Get exam duration for this course (custom or default)
                sinav_suresi = ders_sinavlari_suresi.get(ders['ders_id'], varsayilan_sure)
                
                # Check if total capacity can accommodate this exam
                if ogrenci_sayisi > total_capacity:
                    capacity_errors.append(
                        f"   • {ders['ders_kodu']} - {ders['ders_adi']}: "
                        f"{ogrenci_sayisi} öğrenci (Toplam kapasite: {total_capacity})"
                    )
                
                course_students[ders['ders_id']] = student_ids
                course_info[ders['ders_id']] = {
                    'ders_kodu': ders['ders_kodu'],
                    'ders_adi': ders['ders_adi'],
                    'ogretim_elemani': ders.get('ogretim_elemani', ''),
                    'sinif': ders.get('sinif', 1),
                    'ogrenci_sayisi': ogrenci_sayisi,
                    'sinav_suresi': sinav_suresi  # Each course has its own duration
                }
            
            # If there are capacity errors, return immediately
            if capacity_errors:
                error_msg = "❌ Kapasite Yetersiz!\n\nAşağıdaki dersler için derslik kapasitesi yetersiz:\n\n"
                error_msg += "\n".join(capacity_errors)
                error_msg += "\n\nLütfen daha fazla derslik ekleyin veya mevcut dersliklerin kapasitesini artırın."
                return {
                    'success': False,
                    'message': error_msg
                }
            
            # Store course_info for use in conflict graph building
            self._current_course_info = course_info
            
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
            
            # Check if we have enough days
            if not days:
                return {
                    'success': False,
                    'message': "❌ Seçilen tarih aralığında uygun gün bulunamadı!\n\n"
                              "Lütfen tarih aralığını genişletin veya daha fazla gün seçin."
                }
            
            # Estimate total available slots (colors for graph coloring)
            total_slots_estimate = len(days) * approx_slots_per_day
            # Ensure we have enough colors to avoid premature failure; coloring is only for rough ordering
            total_slots_estimate = max(total_slots_estimate, len(course_info))
            
            logger.info(f"📅 {len(days)} gün mevcut")
            logger.info(f"⏰ ~{approx_slots_per_day} slot/gün, ~{total_slots_estimate} toplam slot")
            logger.info(f"📚 {len(course_info)} ders planlanacak")

            # Build per-class balanced daily targets (e.g., 15 ders, 4 gün → [4,4,4,3])
            from math import ceil
            class_counts: Dict[int, int] = defaultdict(int)
            for cid, info in course_info.items():
                class_counts[info.get('sinif', 0)] += 1
            class_daily_targets: Dict[int, List[int]] = {}
            for sinif, count in class_counts.items():
                q, r = divmod(count, len(days)) if len(days) > 0 else (count, 0)
                vec = [(q + 1) if i < r else q for i in range(len(days))]
                class_daily_targets[sinif] = vec
            self._class_daily_targets = class_daily_targets

            # Pre-warnings for impossible balanced plan under strict per-day class limit
            pre_warnings: List[str] = []
            class_limit_opt = int(params.get('class_per_day_limit', 0) or 0)
            if class_limit_opt > 0 and len(days) > 0:
                for sinif, count in class_counts.items():
                    vec = class_daily_targets.get(sinif, [])
                    max_target = max(vec) if vec else 0
                    if max_target > class_limit_opt:
                        required_days = ceil(count / class_limit_opt)
                        pre_warnings.append(
                            f"{sinif}. sınıf: {count} ders, {len(days)} günde dengeli hedef (max {max_target}) günlük limit {class_limit_opt} ile mümkün değil. "
                            f"En az {required_days} gün gerekir ya da günlük limiti artırın."
                        )
            self._pre_warnings = pre_warnings
            
            # Basic feasibility check
            if len(course_info) > total_slots_estimate * 2:
                return {
                    'success': False,
                    'message': f"❌ Seçilen tarih aralığı sınavları barındırmaya yeterli değil!\n\n"
                              f"   • Planlanacak ders sayısı: {len(course_info)}\n"
                              f"   • Tahmini slot sayısı: ~{total_slots_estimate}\n\n"
                              f"Lütfen tarih aralığını genişletin veya ders sayısını azaltın."
                }
            
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
            # Try many different approaches - don't give up easily!
            max_attempts = int(params.get('max_attempts', 500))  # Much more attempts!
            strategies = [
                'class_interleaved',  # focus on interleaving classes
                'class_interleaved',
                'reverse_degree',    # place least-conflicting first
                'degree_first',      # try hardest first sometimes
                'random',            # diversify
                'class_grouped',     # group by class (still spread by day rules)
                'reverse_degree',
                'class_interleaved'
            ]
            
            best_schedule = []
            best_unscheduled = float('inf')
            any_days_exhausted = False
            attempts_without_improvement = 0
            max_no_improvement = 200# Give up if no improvement for 15 attempts
            
            logger.info(f"🎯 Starting optimization with up to {max_attempts} attempts...")
            logger.info(f"   Target: {len(course_info)} courses to schedule")
            
            for attempt in range(max_attempts):
                strategy = strategies[attempt % len(strategies)]
                
                # Add randomization to each attempt - shuffle days and courses
                shuffled_days = list(days)
                if attempt > 0:  # Keep first attempt deterministic
                    random.shuffle(shuffled_days)
                
                # CRITICAL: Re-run graph coloring every N attempts for completely different placement
                if attempt % 5 == 0:  # Every 5 attempts, redo graph coloring
                    logger.info(f"   🎨 Re-running graph coloring for fresh assignment...")
                    randomized_assignment = self._graph_coloring(
                        list(course_info.keys()),
                        conflicts,
                        course_info,
                        total_slots_estimate,
                        None  # No progress callback for re-coloring
                    )
                    if not randomized_assignment:
                        # Fallback to sequential
                        randomized_assignment = {cid: idx for idx, cid in enumerate(course_info.keys())}
                elif attempt % 10 == 7:  # Some attempts: completely random
                    randomized_assignment = {cid: random.randint(0, len(course_info)) for cid in course_info.keys()}
                else:
                    randomized_assignment = course_slot_assignment
                
                # Update progress (every 10 attempts for smoother UI)
                if progress_callback and (attempt % 10 == 0 or attempt == max_attempts - 1):
                    progress_pct = 70 + int((attempt / max_attempts) * 15)
                    progress_callback(
                        progress_pct,
                        f"Optimizasyon devam ediyor... (Deneme {attempt+1}/{max_attempts}, En iyi: {len(course_info) - best_unscheduled}/{len(course_info)})"
                    )
                
                # Log only every 500 attempts to avoid spam
                if attempt % 500 == 0 or attempt == max_attempts - 1:
                    logger.info(f"🔁 Attempt {attempt+1}/{max_attempts} with strategy={strategy}, randomized={attempt > 0}")
                self._days_exhausted = False
                
                schedule_try = self._assign_times_and_classrooms(
                    randomized_assignment,
                    shuffled_days,
                    derslikler,
                    course_info,
                    course_students,
                    params,
                    progress_callback,
                    order_strategy=strategy,
                    attempt_number=attempt
                )
                
                scheduled_pairs = set((s['ders_id'], s['tarih_saat']) for s in schedule_try)
                scheduled_course_ids = {cid for (cid, _) in scheduled_pairs}
                all_course_ids = set(course_info.keys())
                unscheduled = len(all_course_ids - scheduled_course_ids)
                any_days_exhausted = any_days_exhausted or getattr(self, '_days_exhausted', False)
                
                # Calculate student experience metrics
                student_daily_exams = self._calculate_student_load(schedule_try, course_students)
                max_student_load = max(student_daily_exams.values()) if student_daily_exams else 0
                avg_student_load = sum(student_daily_exams.values()) / len(student_daily_exams) if student_daily_exams else 0
                # Penalize consecutive same-class slots within a day
                class_gap_penalty = self._compute_class_consecutive_penalty(schedule_try, course_info)
                
                # Log only occasionally to reduce spam
                if attempt % 500 == 0 or attempt == max_attempts - 1:
                    logger.info(f"📈 Attempt {attempt+1}: scheduled={len(scheduled_course_ids)}/{len(all_course_ids)}, "
                               f"unscheduled={unscheduled}, max_student_load={max_student_load:.1f}, "
                               f"avg_load={avg_student_load:.2f}")
                
                # Track improvement using multi-criteria optimization
                # Priority: 1) More courses scheduled, 2) Lower max student load, 3) Lower avg load, 4) Fewer consecutive same-class slots
                current_quality = (len(scheduled_course_ids), -max_student_load, -avg_student_load, -class_gap_penalty)
                best_quality = (len(all_course_ids) - best_unscheduled, 
                               getattr(self, '_best_max_load', float('inf')),
                               getattr(self, '_best_avg_load', float('inf')),
                               getattr(self, '_best_class_gap_penalty', float('inf')))
                
                if current_quality > best_quality:
                    best_unscheduled = unscheduled
                    best_schedule = schedule_try
                    self._best_max_load = -max_student_load
                    self._best_avg_load = -avg_student_load
                    self._best_class_gap_penalty = -class_gap_penalty
                    attempts_without_improvement = 0
                    logger.info(f"✨ New best! {len(scheduled_course_ids)} courses, "
                               f"max_load={max_student_load:.1f}, avg={avg_student_load:.2f}")
                else:
                    attempts_without_improvement += 1
                
                # Perfect solution found!
                if unscheduled == 0:
                    logger.info(f"🎉 Perfect solution found at attempt {attempt+1}!")
                    break
                
                # Give up if no improvement for too long
                if attempts_without_improvement >= max_no_improvement and attempt > 20:
                    logger.info(f"⚠️ No improvement for {max_no_improvement} attempts, stopping...")
                    break
            
            schedule = best_schedule
            
            logger.info(f"🏁 Optimization complete: {len(course_info) - best_unscheduled}/{len(course_info)} courses scheduled")
            
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
                
                # Build detailed error message with conflict analysis
                error_msg = f"❌ {len(unscheduled_ids)} ders yerleştirilemedi!\n\n"
                error_msg += f"✅ Yerleştirilen: {len(unique_scheduled_course_ids)}/{len(all_course_ids)} ders\n"
                error_msg += f"❌ Yerleştirilemeyen: {len(unscheduled_ids)} ders\n\n"
                
                # Analyze why courses couldn't be placed
                conflict_analysis = {}
                for ders_id in unscheduled_ids:
                    # Count conflicts with scheduled courses
                    conflicts_with_scheduled = 0
                    for scheduled_id in unique_scheduled_course_ids:
                        if course_students.get(ders_id) and course_students.get(scheduled_id):
                            overlap = len(course_students[ders_id] & course_students[scheduled_id])
                            if overlap > 0:
                                conflicts_with_scheduled += 1
                    conflict_analysis[ders_id] = conflicts_with_scheduled
                
                error_msg += "Yerleştirilemeyen dersler:\n"
                for ders_id in unscheduled_ids[:15]:  # Show max 15
                    info = course_info.get(ders_id, {})
                    conflicts = conflict_analysis.get(ders_id, 0)
                    error_msg += f"   • {info.get('ders_kodu', '?')} - {info.get('ders_adi', '?')}\n"
                    error_msg += f"     └─ {info.get('sinif', '?')}. sınıf, {info.get('ogrenci_sayisi', 0)} öğrenci"
                    if conflicts > 0:
                        error_msg += f", {conflicts} çakışma\n"
                    else:
                        error_msg += f", çakışma yok (zaman yetersiz)\n"
                
                if len(unscheduled_ids) > 15:
                    error_msg += f"   ... ve {len(unscheduled_ids) - 15} ders daha\n"
                
                # Check if it's a timing or conflict issue
                high_conflict_courses = sum(1 for c in conflict_analysis.values() if c > 5)
                no_conflict_courses = sum(1 for c in conflict_analysis.values() if c == 0)
                
                # Get current settings
                no_parallel = params.get('no_parallel_exams', False)
                class_limit = params.get('class_per_day_limit', 0)
                
                error_msg += "\n📊 Analiz:\n"
                error_msg += f"   ⚙️ Mevcut Ayarlar:\n"
                error_msg += f"      • Aynı anda sınav yasağı: {'AÇIK ❌' if no_parallel else 'KAPALI ✅'}\n"
                error_msg += f"      • Günlük sınav limiti: {class_limit if class_limit > 0 else 'YOK ✅'}\n\n"
                
                if no_conflict_courses > len(unscheduled_ids) / 2:
                    error_msg += f"   ⏰ Ana sorun: ZAMAN YETERSİZ ({no_conflict_courses} dersin çakışması yok ama yer bulunamadı)\n"
                    error_msg += "   💡 Çözüm önerileri:\n"
                    error_msg += "      1. Tarih aralığını genişletin\n"
                    error_msg += "      2. Sınav sürelerini kısaltın\n"
                    error_msg += "      3. Daha fazla gün seçin (örn. Cumartesi, Pazar)\n"
                    if no_parallel:
                        error_msg += "      4. 'Aynı anda sınav olmasın' seçeneğini KAPATIN (daha çok sınav aynı saatte yapılabilir)\n"
                else:
                    error_msg += f"   👥 Ana sorun: ÖĞRENCİ ÇAKIŞMALARI ({high_conflict_courses} dersin çok fazla çakışması var)\n"
                    error_msg += "   💡 Çözüm önerileri:\n"
                    if class_limit > 0:
                        error_msg += f"      1. Günlük sınav limitini artırın (şu an: {class_limit})\n"
                    if no_parallel:
                        error_msg += "      2. 'Aynı anda sınav olmasın' seçeneğini KAPATIN\n"
                    error_msg += f"      {'3' if class_limit > 0 or no_parallel else '1'}. Tarih aralığını genişletin\n"
                    error_msg += f"      {'4' if class_limit > 0 or no_parallel else '2'}. Bazı dersleri programdan çıkarın\n"
                
                return {
                    'success': False,
                    'message': error_msg,
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
            # Pre-warnings from balanced targets feasibility
            pre_warnings = getattr(self, '_pre_warnings', []) or []
            
            if progress_callback:
                progress_callback(100, "Tamamlandı!")
            
            logger.info(f"✅ Exam schedule created: {len(schedule)} exam entries")
            used_rooms = sorted({s['derslik_kodu'] for s in schedule})
            logger.info(f"🏫 Kullanılan derslikler: {len(used_rooms)} → {used_rooms}")
            
            # Count unique exams (grouped by course + time)
            unique_exams = set((s['ders_id'], s['tarih_saat']) for s in schedule)
            logger.info(f"📝 {len(unique_exams)} unique exams scheduled")
            
            # Calculate final student experience metrics
            student_daily_exams = self._calculate_student_load(schedule, course_students)
            daily_limit = params.get('class_per_day_limit', 0) or 0
            if student_daily_exams:
                max_student_load = max(student_daily_exams.values())
                avg_student_load = sum(student_daily_exams.values()) / len(student_daily_exams)
                students_with_heavy_load = sum(1 for load in student_daily_exams.values() if load >= 4)
                students_exceeding_limit = sum(1 for load in student_daily_exams.values() if load > daily_limit) if daily_limit > 0 else 0
                
                logger.info(f"👥 Öğrenci Yükü: max={max_student_load} sınav/gün, ortalama={avg_student_load:.2f}")
                logger.info(f"⚠️ Günde 4+ sınava giren öğrenci sayısı: {students_with_heavy_load}")
                if daily_limit > 0 and students_exceeding_limit > 0:
                    logger.warning(f"⚠️ Günlük limiti ({daily_limit}) aşan öğrenci sayısı: {students_exceeding_limit}")
                
                success_msg = f"✅ {len(unique_exams)} sınav başarıyla programlandı!\n\n"
                success_msg += f"📊 Öğrenci Yükü:\n"
                success_msg += f"   • En fazla: {max_student_load} sınav/gün\n"
                success_msg += f"   • Ortalama: {avg_student_load:.1f} sınav/gün\n"
                if daily_limit > 0:
                    success_msg += f"   • Günlük limit: {daily_limit} sınav/gün\n"
                    if students_exceeding_limit > 0:
                        success_msg += f"   • ⚠️ {students_exceeding_limit} öğrenci limiti aşıyor\n"
                if students_with_heavy_load > 0:
                    success_msg += f"   • ⚠️ {students_with_heavy_load} öğrenci günde 4+ sınava giriyor\n"
            else:
                success_msg = f"✅ {len(unique_exams)} sınav başarıyla programlandı!"
                max_student_load = 0
                avg_student_load = 0
            
            result = {
                'success': True,
                'message': success_msg,
                'schedule': schedule,
                'stats': {
                    'total_courses': len(dersler),
                    'scheduled_courses': len(unique_exams),
                    'days_used': len(set(s['tarih_saat'].date() for s in schedule)),
                    'max_student_load': max_student_load,
                    'avg_student_load': round(avg_student_load, 2) if student_daily_exams else 0
                },
                'warnings': pre_warnings
            }
            return result
            
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
    
    def _calculate_student_load(self, schedule: List[Dict], course_students: Dict[int, Set[str]]) -> Dict[str, int]:
        """
        Calculate maximum number of exams per day for each student
        Returns: Dict[student_no, max_exams_per_day]
        """
        from collections import defaultdict
        
        # Group exams by date and student
        student_daily_count = defaultdict(lambda: defaultdict(int))
        
        for exam in schedule:
            ders_id = exam['ders_id']
            exam_date = exam['tarih_saat'].date() if hasattr(exam['tarih_saat'], 'date') else exam['tarih_saat']
            
            # For each student in this course, increment their daily count
            for student_no in course_students.get(ders_id, set()):
                student_daily_count[student_no][exam_date] += 1
        
        # Calculate maximum exams per day for each student
        student_max_load = {}
        for student_no, daily_counts in student_daily_count.items():
            student_max_load[student_no] = max(daily_counts.values()) if daily_counts else 0
        
        return student_max_load
    
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
        Build conflict graph where edges represent conflicts:
        1. Student conflicts (same students in different courses)
        2. Same class conflicts (courses from same year should be on different days)
        Returns adjacency list
        """
        conflicts = defaultdict(set)
        course_ids = list(course_students.keys())
        threshold = int(params.get('min_conflict_overlap', 1))
        total_edges = 0
        student_conflict_edges = 0
        class_conflict_edges = 0
        max_overlap = 0
        sample_overlaps = []
        
        # Get course info from instance variable (set during plan_exam_schedule)
        course_info = getattr(self, '_current_course_info', {})
        
        # Check EVERY course against EVERY other course (no optimization)
        for ders_id1 in course_ids:
            for ders_id2 in course_ids:
                # Skip comparing a course with itself
                if ders_id1 == ders_id2:
                    continue
                
                # Skip duplicate pairs (A,B) same as (B,A) - only count once
                if ders_id1 > ders_id2:
                    continue
                
                has_conflict = False
                
                # Rule 1: Check if courses share any students
                shared_students = course_students[ders_id1] & course_students[ders_id2]
                overlap_count = len(shared_students)
                max_overlap = max(max_overlap, overlap_count)
                if overlap_count >= threshold:
                    has_conflict = True
                    student_conflict_edges += 1
                    if len(sample_overlaps) < 10:
                        sample_overlaps.append((ders_id1, ders_id2, overlap_count))
                
                # Rule 2: Same class courses - DON'T add to conflict graph!
                # We handle this during placement with daily limits, not in graph coloring
                # Graph coloring is ONLY for student conflicts (parallel exams)
                # Class distribution is handled by daily placement limits
                if course_info and overlap_count >= threshold:
                    sinif1 = course_info.get(ders_id1, {}).get('sinif')
                    sinif2 = course_info.get(ders_id2, {}).get('sinif')
                    if sinif1 and sinif2 and sinif1 == sinif2:
                        # Same class AND student conflict - just for logging
                        class_conflict_edges += 1
                
                if has_conflict:
                    conflicts[ders_id1].add(ders_id2)
                    conflicts[ders_id2].add(ders_id1)
                    total_edges += 1
        
        # Log graph density info for diagnostics
        try:
            num_nodes = len(course_ids)
            avg_degree = (2 * total_edges / num_nodes) if num_nodes else 0
            logger.info(f"🧮 Conflict Graph: nodes={num_nodes}, total_edges={total_edges}, avg_degree={avg_degree:.2f}")
            logger.info(f"   ├─ Öğrenci çakışmaları: {student_conflict_edges} edges")
            logger.info(f"   ├─ Sınıf çakışmaları: {class_conflict_edges} edges")
            logger.info(f"   └─ Max öğrenci overlap: {max_overlap}")
            if sample_overlaps:
                logger.info(f"🧪 Overlap samples (ders_id1, ders_id2, count): {sample_overlaps[:5]}")
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
        # Add random component to break ties differently each time
        sorted_courses = sorted(
            courses,
            key=lambda x: (
                -degrees[x],           # More conflicts first
                random.random()         # Random tiebreaker
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
            
            # Pick a slot (color) that doesn't conflict
            # Sometimes pick earliest (deterministic), sometimes pick nearby (randomized)
            available_colors = [c for c in range(max_colors) if c not in used_colors]
            
            if not available_colors:
                logger.warning(f"❌ Cannot color {course_info[ders_id]['ders_kodu']} - not enough slots!")
                return None
            
            # Strategy: 70% pick first available, 30% pick one of first 5 randomly
            if random.random() < 0.7 or len(available_colors) == 1:
                best_slot = available_colors[0]
            else:
                # Pick from first few available slots randomly
                choices = available_colors[:min(5, len(available_colors))]
                best_slot = random.choice(choices)
            
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
        order_strategy: str = 'small_first',
        attempt_number: int = 0
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
        
        # Calculate total capacity for capacity_aware strategy
        total_capacity = sum(d['kapasite'] for d in derslikler)
        
        # Time parameters
        ara_suresi = params.get('ara_suresi', 15)
        ogle_baslangic = self._parse_time(params.get('ogle_arasi_baslangic', '12:00'))
        ogle_bitis = self._parse_time(params.get('ogle_arasi_bitis', '13:30'))
        gunluk_ilk = self._parse_time(params.get('gunluk_ilk_sinav', '10:00'))
        gunluk_son = self._parse_time(params.get('gunluk_son_sinav', '19:15'))
        
        current_day_idx = 0
        current_time = None
        day_slot_index = 0
        
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
        # Track class usage PER DAY (not just per slot!)
        day_class_count: Dict[tuple, int] = defaultdict(int)  # (day_index, sinif) -> count
        # Balanced daily targets per class
        class_daily_targets = getattr(self, '_class_daily_targets', {})
        # Track student exams PER DAY to prevent overloading
        student_day_exams: Dict[tuple, Set[int]] = defaultdict(set)  # (day_index, student_no) -> set of ders_ids
        # Track previous slot classes per day to avoid back-to-back same-class
        last_slot_classes_by_day: Dict[int, Set[int]] = defaultdict(set)
        # Track last day used per class to avoid consecutive days if days remain
        last_day_for_class: Dict[int, int] = {}
        # Optional explicit student per-day limit (separate from class limit)
        student_day_limit = int(params.get('student_per_day_limit', 0) or 0)
        # Minimum gap in slots for the same class within a day
        min_class_gap_slots = int(params.get('min_class_gap_slots', 1) or 1)
        # Track last slot index per (day, class)
        last_slot_idx_for_class: Dict[tuple, int] = {}
        
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
                    day_slot_index = 0
                
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
                # Different ordering strategies to maximize placement success
                if order_strategy == 'random':
                    # Random order
                    candidate = list(remaining_courses)
                    random.shuffle(candidate)
                elif order_strategy == 'degree_first':
                    # Most conflicts first (harder to place)
                    conflicts_map = defaultdict(int)
                    for cid in remaining_courses:
                        for other_cid in remaining_courses:
                            if cid != other_cid and course_students.get(cid) and course_students.get(other_cid):
                                if len(course_students[cid] & course_students[other_cid]) >= conflict_threshold:
                                    conflicts_map[cid] += 1
                    candidate = sorted(remaining_courses, key=lambda x: conflicts_map.get(x, 0), reverse=True)
                elif order_strategy == 'reverse_degree':
                    # Least conflicts first (easier to place)
                    conflicts_map = defaultdict(int)
                    for cid in remaining_courses:
                        for other_cid in remaining_courses:
                            if cid != other_cid and course_students.get(cid) and course_students.get(other_cid):
                                if len(course_students[cid] & course_students[other_cid]) >= conflict_threshold:
                                    conflicts_map[cid] += 1
                    candidate = sorted(remaining_courses, key=lambda x: conflicts_map.get(x, 0))
                elif order_strategy == 'class_grouped':
                    # Group by class year
                    candidate = sorted(remaining_courses, key=lambda x: (course_info[x].get('sinif', 0), course_info[x]['ogrenci_sayisi']))
                elif order_strategy == 'class_interleaved':
                    # CRITICAL: Interleave courses from different classes
                    # This prevents same class courses from being placed consecutively
                    # which would trigger daily limits quickly
                    by_class = {}
                    for cid in remaining_courses:
                        sinif = course_info[cid].get('sinif', 0)
                        if sinif not in by_class:
                            by_class[sinif] = []
                        by_class[sinif].append(cid)
                    
                    # Sort within each class by student count
                    for sinif in by_class:
                        by_class[sinif].sort(key=lambda x: course_info[x]['ogrenci_sayisi'])
                    
                    # Interleave: take one from each class in round-robin fashion
                    candidate = []
                    max_len = max(len(courses) for courses in by_class.values()) if by_class else 0
                    for i in range(max_len):
                        for sinif in sorted(by_class.keys()):
                            if i < len(by_class[sinif]):
                                candidate.append(by_class[sinif][i])
                else:
                    # Default: conflict-light first
                    conflicts_map = defaultdict(int)
                    for cid in remaining_courses:
                        for other_cid in remaining_courses:
                            if cid != other_cid and course_students.get(cid) and course_students.get(other_cid):
                                if len(course_students[cid] & course_students[other_cid]) >= conflict_threshold:
                                    conflicts_map[cid] += 1
                    candidate = sorted(remaining_courses, key=lambda x: conflicts_map.get(x, 0))
                selected: List[int] = []
                skipped_reasons = defaultdict(int)  # Track why courses are skipped
                
                for cid in candidate:
                    # Rule 1: If no_parallel_exams is enabled, only one exam per slot
                    if no_parallel and selected:
                        skipped_reasons['no_parallel_enabled'] += 1
                        continue
                    
                    # Rule 2: Student conflict check - MUST NOT have overlapping students
                    if course_students.get(cid):
                        overlap = len(course_students[cid] & batch_used_students)
                        if overlap >= conflict_threshold:
                            skipped_reasons[f'student_conflict_{overlap}_students'] += 1
                            continue
                    
                    # Rule 3: Class per day limit - SMART DISTRIBUTION
                    # Goal: Spread courses across days (e.g. 8 courses → 5 days: 3×2 + 2×1)
                    # Strategy: Only place course today if other days aren't better options
                    csinif = course_info[cid].get('sinif', 0)
                    if class_limit > 0:
                        # Check slot limit
                        if batch_used_classes[csinif] >= class_limit:
                            skipped_reasons[f'class_slot_limit_exceeded_class_{csinif}'] += 1
                            continue
                        
                        # Smart daily limit: prefer spreading across days
                        day_key = (current_day_idx, csinif)
                        current_day_count = day_class_count[day_key]
                        remaining_days = len(days) - current_day_idx - 1
                        
                        # Dynamic limit: AGGRESSIVE spreading in early phase
                        # Goal: 8 courses → 5 days = 3×2 + 2×1 distribution
                        if remaining_days >= 2 and current_day_count >= 2:
                            # Already have 2 courses today, and 2+ days left → skip to next day
                            skipped_reasons[f'spreading_across_days_class_{csinif}'] += 1
                            continue
                        elif remaining_days >= 3 and current_day_count >= 1:
                            # Already have 1 course today, and 3+ days left → skip to next day
                            skipped_reasons[f'spreading_across_days_class_{csinif}'] += 1
                            continue
                        elif current_day_count >= class_limit:
                            # Hard limit reached
                            skipped_reasons[f'class_day_limit_exceeded_class_{csinif}'] += 1
                            continue

                        # Balanced target push: if today's count exceeds target while future days remain, skip
                        target_vec = class_daily_targets.get(csinif)
                        if target_vec and current_day_idx < len(target_vec):
                            target_for_today = target_vec[current_day_idx]
                            if current_day_count >= target_for_today and remaining_days > 0:
                                skipped_reasons['class_daily_balanced_target'] += 1
                                continue

                    # Rule 3b: Avoid back-to-back same-class in consecutive slots (if days remain)
                    prev_classes = last_slot_classes_by_day.get(current_day_idx, set())
                    if csinif in prev_classes and (len(days) - current_day_idx - 1) > 0:
                        skipped_reasons['class_prev_slot_gap'] += 1
                        continue
                    # Rule 3b.2: Enforce minimum slot gap for same class within a day
                    last_idx = last_slot_idx_for_class.get((current_day_idx, csinif))
                    if last_idx is not None and (day_slot_index - last_idx) < min_class_gap_slots and (len(days) - current_day_idx - 1) > 0:
                        skipped_reasons['class_min_gap_slots'] += 1
                        continue

                    # Rule 3c: Avoid scheduling same class on consecutive days when there are remaining days
                    last_day_idx_used = last_day_for_class.get(csinif)
                    if last_day_idx_used is not None and last_day_idx_used == current_day_idx - 1 and (len(days) - current_day_idx - 1) > 0:
                        skipped_reasons['class_consecutive_day_avoid'] += 1
                        continue
                    
                    # Rule 4: Student per day limit - check if ANY student would exceed limit
                    # Only enforce explicit student_per_day_limit if provided
                    limit_for_students = student_day_limit if student_day_limit > 0 else 0
                    if limit_for_students > 0:
                        students_in_course = course_students.get(cid, set())
                        student_would_exceed = False
                        for student_no in students_in_course:
                            student_day_key = (current_day_idx, student_no)
                            current_exams = len(student_day_exams[student_day_key])
                            if current_exams >= limit_for_students:
                                student_would_exceed = True
                                skipped_reasons[f'student_day_limit_exceeded'] += 1
                                break
                        if student_would_exceed:
                            continue
                    
                    # Course can be added to this batch!
                    selected.append(cid)
                    batch_used_students.update(course_students.get(cid, set()))
                    batch_used_classes[csinif] += 1
                    # Update daily count
                    day_key = (current_day_idx, csinif)
                    day_class_count[day_key] += 1
                    # Update student daily exam count
                    for student_no in course_students.get(cid, set()):
                        student_day_key = (current_day_idx, student_no)
                        student_day_exams[student_day_key].add(cid)
                
                # If selection too small, try a relaxed second pass ignoring spreading/gap rules
                if not no_parallel and len(selected) <= 1 and remaining_courses:
                    target_parallel = min(3, len(all_rooms))
                    for cid in candidate:
                        if cid in selected:
                            continue
                        if len(selected) >= target_parallel:
                            break
                        # Respect no_parallel flag
                        if no_parallel and selected:
                            break
                        # Respect student conflict
                        if course_students.get(cid):
                            overlap = len(course_students[cid] & batch_used_students)
                            if overlap >= conflict_threshold:
                                continue
                        # Respect class slot/day hard limits only
                        csinif = course_info[cid].get('sinif', 0)
                        if class_limit > 0 and batch_used_classes[csinif] >= class_limit:
                            continue
                        day_key_relax = (current_day_idx, csinif)
                        if class_limit > 0 and day_class_count[day_key_relax] >= class_limit:
                            continue
                        # Respect same-day class min gap
                        last_idx = last_slot_idx_for_class.get((current_day_idx, csinif))
                        if last_idx is not None and (day_slot_index - last_idx) < min_class_gap_slots and (len(days) - current_day_idx - 1) > 0:
                            continue
                        # Avoid consecutive days if days remain
                        last_day_idx_used = last_day_for_class.get(csinif)
                        if last_day_idx_used is not None and last_day_idx_used == current_day_idx - 1 and (len(days) - current_day_idx - 1) > 0:
                            continue
                        # Respect explicit student day limit if set
                        if student_day_limit > 0:
                            students_in_course = course_students.get(cid, set())
                            blocked = False
                            for student_no in students_in_course:
                                if len(student_day_exams[(current_day_idx, student_no)]) >= student_day_limit:
                                    blocked = True
                                    break
                            if blocked:
                                continue
                        # Passed relaxed checks → add
                        selected.append(cid)
                        batch_used_students.update(course_students.get(cid, set()))
                        batch_used_classes[csinif] += 1
                        day_class_count[(current_day_idx, csinif)] += 1

                # Log parallel exam stats for debugging
                if selected and len(selected) > 1:
                    logger.info(f"   ✨ PARALEL: {len(selected)} sınav aynı slota yerleştirildi: {[course_info[c]['ders_kodu'] for c in selected]}")
                elif selected and len(selected) == 1:
                    logger.info(f"   ⚠️  TEK: Sadece 1 sınav yerleştirildi: {course_info[selected[0]]['ders_kodu']}")
                    if skipped_reasons:
                        logger.info(f"       Neden: {dict(skipped_reasons)}")
                
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
                    used_in_slot = set()  # Track rooms used in this slot to prevent conflicts
                    
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
                        used_in_slot.add(best['derslik_id'])
                        available.remove(best)
                    
                    # fill remaining capacity - only use rooms not yet used in this slot
                    available_for_fill = [r for r in available if r['derslik_id'] not in used_in_slot]
                    for r in sorted(available_for_fill, key=lambda x: (room_usage_count[x['derslik_id']], x['kapasite'])):
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
                        used_in_slot.add(r['derslik_id'])
                    
                    # finalize
                    placed_this_batch = selected
                    max_duration_in_batch = max(duration_map[c] for c in selected) if selected else 0
                    # Enforce same-class intra-day minimum gap of 1 slot (if possible)
                    # Build class map of exams already placed today to discourage back-to-back
                    today_date = slot_time.date()
                    class_in_slot = set(course_info[c]['sinif'] for c in selected)
                    # Append entries
                    for e in entries:
                        schedule.append(e)
                    # Update previous slot classes and last day usage
                    last_slot_classes_by_day[current_day_idx] = set(class_in_slot)
                    for sclass in class_in_slot:
                        last_day_for_class[sclass] = current_day_idx
                        last_slot_idx_for_class[(current_day_idx, sclass)] = day_slot_index
                
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
                # Advance per-day slot index if staying in same day
                if current_time is not None and current_time.date() == days[current_day_idx].date():
                    day_slot_index += 1

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

    def _compute_class_consecutive_penalty(self, schedule: List[Dict], course_info: Dict[int, Dict]) -> int:
        """
        Compute penalty for same-class exams being scheduled back-to-back within the same day.
        Penalty counts occurrences where two consecutive slots (by start time) share the same class.
        """
        try:
            # Group by day
            by_day: Dict[str, List[Tuple[datetime, int]]] = defaultdict(list)
            for e in schedule:
                ts = e['tarih_saat'] if isinstance(e['tarih_saat'], datetime) else datetime.fromisoformat(str(e['tarih_saat']))
                by_day[str(ts.date())].append((ts, e['ders_id']))
            penalty = 0
            for _, items in by_day.items():
                items.sort(key=lambda x: x[0])
                # Collapse parallel entries to unique slot starts per class
                # Build per-slot classes
                slot_map: Dict[datetime, Set[int]] = defaultdict(set)
                for ts, did in items:
                    slot_map[ts].add(course_info.get(did, {}).get('sinif', 0))
                ordered_slots = sorted(slot_map.keys())
                for i in range(1, len(ordered_slots)):
                    prev_classes = slot_map[ordered_slots[i-1]]
                    curr_classes = slot_map[ordered_slots[i]]
                    # Penalty if any class appears in consecutive slots
                    if prev_classes & curr_classes:
                        penalty += 1
            return penalty
        except Exception:
            return 0

    def _safe_int(self, d: Dict, key: str, default: int) -> int:
        try:
            return int(d.get(key, default))
        except Exception:
            return default
