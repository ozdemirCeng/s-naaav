"""
Sınav Model - CRUD Operations
"""

import logging
from typing import List, Dict, Optional
from models.database import DatabaseManager

logger = logging.getLogger(__name__)


class SinavModel:
    """Exam data access layer"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def get_programs_by_bolum(self, bolum_id: int) -> List[Dict]:
        """Get all exam programs for a department"""
        query = """
            SELECT program_id, bolum_id, program_adi, sinav_tipi, 
                   baslangic_tarihi, bitis_tarihi
            FROM sinav_programi
            WHERE bolum_id = %s
            ORDER BY baslangic_tarihi DESC
        """
        return self.db.execute_query(query, (bolum_id,))
    
    def get_sinavlar_by_program(self, program_id: int) -> List[Dict]:
        """Get all exams in a program"""
        query = """
            SELECT s.sinav_id, s.program_id, s.ders_id, s.tarih, 
                   s.baslangic_saati, s.bitis_saati, s.ogrenci_sayisi,
                   d.ders_kodu, d.ders_adi,
                   STRING_AGG(dr.derslik_kodu, ', ') as derslik_kodu
            FROM sinavlar s
            JOIN dersler d ON s.ders_id = d.ders_id
            LEFT JOIN sinav_derslikleri sd ON s.sinav_id = sd.sinav_id
            LEFT JOIN derslikler dr ON sd.derslik_id = dr.derslik_id
            WHERE s.program_id = %s
            GROUP BY s.sinav_id, d.ders_kodu, d.ders_adi
            ORDER BY s.tarih, s.baslangic_saati
        """
        return self.db.execute_query(query, (program_id,))
    
    def create_program(self, program_data: Dict) -> int:
        """Create exam program"""
        query = """
            INSERT INTO sinav_programi
            (bolum_id, program_adi, sinav_tipi, baslangic_tarihi, bitis_tarihi)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING program_id
        """
        params = (
            program_data['bolum_id'],
            program_data['program_adi'],
            program_data.get('sinav_tipi', 'Final'),
            program_data['baslangic_tarihi'],
            program_data['bitis_tarihi']
        )
        
        result = self.db.execute_query(query, params)
        logger.info(f"✅ Exam program created: {program_data['program_adi']}")
        return result[0]['program_id']
    
    def insert_sinav(self, sinav_data: Dict) -> int:
        """Insert new exam"""
        query = """
            INSERT INTO sinavlar
            (program_id, ders_id, tarih, baslangic_saati, bitis_saati)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING sinav_id
        """
        params = (
            sinav_data['program_id'],
            sinav_data['ders_id'],
            sinav_data['tarih'],
            sinav_data['baslangic_saati'],
            sinav_data['bitis_saati']
        )
        
        result = self.db.execute_query(query, params)
        logger.info(f"✅ Exam created: {sinav_data['ders_id']}")
        return result[0]['sinav_id']
    
    def assign_derslik(self, sinav_id: int, derslik_id: int) -> bool:
        """Assign classroom to exam"""
        query = """
            INSERT INTO sinav_derslikleri (sinav_id, derslik_id)
            VALUES (%s, %s)
            ON CONFLICT (sinav_id, derslik_id) DO NOTHING
        """
        self.db.execute_query(query, (sinav_id, derslik_id), fetch=False)
        logger.info(f"✅ Classroom assigned to exam: {sinav_id}")
        return True
    
    def delete_program(self, program_id: int) -> bool:
        """Delete exam program"""
        query = "DELETE FROM sinav_programi WHERE program_id = %s"
        self.db.execute_query(query, (program_id,), fetch=False)
        logger.info(f"✅ Exam program deleted: {program_id}")
        return True
