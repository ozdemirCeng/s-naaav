"""
Öğrenci Model - CRUD Operations
"""

import logging
from typing import List, Dict, Optional
from models.database import DatabaseManager

logger = logging.getLogger(__name__)


class OgrenciModel:
    """Student data access layer"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def get_ogrenciler_by_bolum(self, bolum_id: int) -> List[Dict]:
        """Get all students for a department"""
        query = """
            SELECT ogrenci_no, bolum_id, ad_soyad, sinif, aktif
            FROM ogrenciler
            WHERE bolum_id = %s AND aktif = TRUE
            ORDER BY sinif, ogrenci_no
        """
        return self.db.execute_query(query, (bolum_id,))
    
    def get_ogrenci_by_no(self, ogrenci_no: str) -> Optional[Dict]:
        """Get student by student number"""
        query = """
            SELECT o.*, b.bolum_adi
            FROM ogrenciler o
            JOIN bolumler b ON o.bolum_id = b.bolum_id
            WHERE o.ogrenci_no = %s
        """
        result = self.db.execute_query(query, (ogrenci_no,))
        return result[0] if result else None
    
    def get_ogrenciler_by_ders(self, ders_id: int) -> List[Dict]:
        """Get all students taking a specific course"""
        query = """
            SELECT DISTINCT o.*
            FROM ogrenciler o
            JOIN ders_kayitlari dk ON o.ogrenci_no = dk.ogrenci_no
            WHERE dk.ders_id = %s AND o.aktif = TRUE
            ORDER BY o.ad_soyad
        """
        return self.db.execute_query(query, (ders_id,))
    
    def insert_ogrenci(self, ogrenci_data: Dict) -> str:
        """Insert new student"""
        query = """
            INSERT INTO ogrenciler
            (ogrenci_no, bolum_id, ad_soyad, sinif)
            VALUES (%s, %s, %s, %s)
            RETURNING ogrenci_no
        """
        params = (
            ogrenci_data['ogrenci_no'],
            ogrenci_data['bolum_id'],
            ogrenci_data['ad_soyad'],
            ogrenci_data.get('sinif', 1)
        )
        
        result = self.db.execute_query(query, params)
        logger.info(f"✅ Student created: {ogrenci_data['ogrenci_no']}")
        return result[0]['ogrenci_no']
    
    def update_ogrenci(self, ogrenci_no: str, ogrenci_data: Dict) -> bool:
        """Update student"""
        query = """
            UPDATE ogrenciler
            SET ad_soyad = %s,
                sinif = %s
            WHERE ogrenci_no = %s
        """
        params = (
            ogrenci_data['ad_soyad'],
            ogrenci_data.get('sinif', 1),
            ogrenci_no
        )
        
        self.db.execute_query(query, params, fetch=False)
        logger.info(f"✅ Student updated: {ogrenci_no}")
        return True
    
    def delete_ogrenci(self, ogrenci_no: str) -> bool:
        """Delete student (soft delete)"""
        query = "UPDATE ogrenciler SET aktif = FALSE WHERE ogrenci_no = %s"
        self.db.execute_query(query, (ogrenci_no,), fetch=False)
        logger.info(f"✅ Student deleted: {ogrenci_no}")
        return True
