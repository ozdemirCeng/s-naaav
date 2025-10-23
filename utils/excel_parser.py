"""
Excel Parser Utilities - Improved Version
Parse Excel files for course and student data with flexible formatting
"""

import logging
import re
from pathlib import Path
from typing import List, Dict
import openpyxl
import pandas as pd

logger = logging.getLogger(__name__)


class ExcelParser:
    """Excel file parser for importing data"""

    @staticmethod
    def parse_ders_listesi(file_path: str) -> List[Dict]:
        """
        Parse course list from Excel file
        Supports multiple formats including section-based layout

        Args:
            file_path: Path to Excel file

        Returns:
            List of course dictionaries
        """
        try:
            # Read Excel file without assuming header row
            df = pd.read_excel(file_path, header=None)

            # Try to detect the format
            # Check if it has standard column headers in first few rows
            has_header = False
            header_row = 0

            for i in range(min(5, len(df))):
                row_text = ' '.join([str(x).lower() for x in df.iloc[i].values if pd.notna(x)])
                if 'ders kodu' in row_text or 'ders kod' in row_text:
                    has_header = True
                    header_row = i
                    break

            if has_header:
                return ExcelParser._parse_with_repeating_headers(file_path, header_row)
            else:
                return ExcelParser._parse_text_based_ders_listesi(df)

        except Exception as e:
            logger.error(f"Excel parse hatası: {e}")
            raise ValueError(f"Excel dosyası okunamadı: {str(e)}")

    @staticmethod
    def _parse_with_repeating_headers(file_path: str, first_header_row: int) -> List[Dict]:
        """
        Parse format with repeating section headers (like your image)
        Each section has: DERS KODU | DERSİN ADI | DERSİ VEREN ÖĞR. ELEMANI
        """
        df = pd.read_excel(file_path, header=None)

        dersler = []
        current_sinif = 1
        current_yapisi = 'Zorunlu'

        for idx, row in df.iterrows():
            # Convert row to list of strings
            row_values = [str(x).strip() if pd.notna(x) else '' for x in row.values]
            row_text = ' '.join(row_values)

            if not row_text or row_text == '':
                continue

            # Check for class header (e.g., "1. Sınıf", "2. Sınıf", "3. Sınıf")
            sinif_match = re.search(r'(\d+)\s*\.?\s*s[ıiİI]n[ıiİI]f', row_text, re.IGNORECASE)
            if sinif_match:
                current_sinif = int(sinif_match.group(1))
                current_yapisi = 'Zorunlu'
                continue

            # Check for elective course section
            if re.search(r'se[çc]meli|se[çc]imlik', row_text, re.IGNORECASE):
                current_yapisi = 'Seçmeli'
                continue

            # Skip header rows
            if re.search(r'ders\s*kodu|ders\s*kod[ıi]', row_text, re.IGNORECASE):
                continue

            # Parse course row (3 columns: DERS KODU | DERSİN ADI | DERSİ VEREN)
            # First column should be course code (e.g., AIT109, BLM103)
            ders_kodu = row_values[0] if len(row_values) > 0 else ''

            # Check if it looks like a course code (letters + numbers)
            if not re.match(r'^[A-Z]{3}\d{3}', ders_kodu):
                continue

            ders_adi = row_values[1] if len(row_values) > 1 else 'İsimsiz Ders'
            ogretim_elemani = row_values[2] if len(row_values) > 2 else 'Belirtilmemiş'

            # Clean up the values
            ders_adi = ders_adi.strip()
            ogretim_elemani = ogretim_elemani.strip()

            # Skip if course name is empty or looks like a header
            if not ders_adi or re.search(r'dersin\s*ad[ıi]', ders_adi, re.IGNORECASE):
                continue

            ders = {
                'ders_kodu': ders_kodu.upper(),
                'ders_adi': ders_adi if ders_adi else 'İsimsiz Ders',
                'ogretim_elemani': ogretim_elemani if ogretim_elemani else 'Belirtilmemiş',
                'sinif': current_sinif,
                'ders_yapisi': current_yapisi
            }
            dersler.append(ders)

        logger.info(f"✅ {len(dersler)} ders Excel'den yüklendi (bölüm formatı)")
        return dersler

    @staticmethod
    def _parse_text_based_ders_listesi(df: pd.DataFrame) -> List[Dict]:
        """Parse text-based format where courses are listed in rows"""
        dersler = []
        current_sinif = 1
        current_yapisi = 'Zorunlu'

        for idx, row in df.iterrows():
            # Convert row to string for pattern matching
            row_text = ' '.join([str(x) for x in row.values if pd.notna(x)]).strip()

            if not row_text or row_text == 'nan':
                continue

            # Check for class header (e.g., "1. Sınıf", "2. Sınıf")
            sinif_match = re.search(r'(\d+)\s*\.?\s*s[ıi]n[ıi]f', row_text, re.IGNORECASE)
            if sinif_match:
                current_sinif = int(sinif_match.group(1))
                current_yapisi = 'Zorunlu'
                continue

            # Check for elective course section
            if re.search(r'se[çc]meli|se[çc]imlik', row_text, re.IGNORECASE):
                current_yapisi = 'Seçmeli'
                continue

            # Skip header rows
            if re.search(r'ders\s+kodu|dersin\s+ad[ıi]', row_text, re.IGNORECASE):
                continue

            # Try to extract course information
            # Pattern: DERS_KODU Ders Adı Öğretim Elemanı
            kod_match = re.match(r'^([A-Z]{3}\d{3})', row_text)

            if kod_match:
                ders_kodu = kod_match.group(1)
                remaining = row_text[len(ders_kodu):].strip()

                # Split remaining text to get name and instructor
                instructor_pattern = r'((?:Prof\.|Doç\.|Dr\.|Öğr\.|Arş\.).*?)$'
                instructor_match = re.search(instructor_pattern, remaining)

                if instructor_match:
                    ogretim_elemani = instructor_match.group(1).strip()
                    ders_adi = remaining[:instructor_match.start()].strip()
                else:
                    ders_adi = remaining
                    ogretim_elemani = 'Belirtilmemiş'

                ders = {
                    'ders_kodu': ders_kodu,
                    'ders_adi': ders_adi if ders_adi else 'İsimsiz Ders',
                    'ogretim_elemani': ogretim_elemani,
                    'sinif': current_sinif,
                    'ders_yapisi': current_yapisi
                }
                dersler.append(ders)

        logger.info(f"✅ {len(dersler)} ders Excel'den yüklendi (metin formatı)")
        return dersler

    @staticmethod
    def parse_ogrenci_listesi(file_path: str) -> List[Dict]:
        """
        Parse student list from Excel file
        Supports standard tabular format: Öğrenci No | Ad Soyad | Sınıf | Ders

        Args:
            file_path: Path to Excel file

        Returns:
            List of student dictionaries with enrolled courses
        """
        try:
            # Try reading with first row as header
            df = pd.read_excel(file_path)

            # Normalize column names
            df.columns = df.columns.str.strip().str.lower()

            # Remove Turkish characters for matching
            df.columns = df.columns.str.replace('ı', 'i').str.replace('ş', 's').str.replace('ğ', 'g')
            df.columns = df.columns.str.replace('ü', 'u').str.replace('ö', 'o').str.replace('ç', 'c')

            # Column mapping
            column_mapping = {
                'ogrenci no': 'ogrenci_no',
                'ogrencino': 'ogrenci_no',
                'no': 'ogrenci_no',
                'numara': 'ogrenci_no',
                'ad soyad': 'ad_soyad',
                'adsoyad': 'ad_soyad',
                'ad': 'ad_soyad',
                'isim': 'ad_soyad',
                'sinif': 'sinif',
                'sinifi': 'sinif',
                'ders': 'ders',
                'ders kodu': 'ders',
                'derskodu': 'ders'
            }

            # Rename columns
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df.rename(columns={old_name: new_name}, inplace=True)

            # Validate required columns
            required = ['ogrenci_no', 'ad_soyad']
            missing = [col for col in required if col not in df.columns]

            if missing:
                raise ValueError(f"Eksik sütunlar: {', '.join(missing)}")

            # Group by student to collect their courses
            ogrenciler_dict = {}

            for _, row in df.iterrows():
                ogrenci_no = str(row['ogrenci_no']).strip()
                ad_soyad = str(row['ad_soyad']).strip()

                # Extract class number
                sinif_val = str(row.get('sinif', '1')).strip()
                sinif_match = re.search(r'(\d+)', sinif_val)
                sinif = int(sinif_match.group(1)) if sinif_match else 1

                # Get course if exists
                ders = str(row.get('ders', '')).strip() if 'ders' in row and pd.notna(row.get('ders')) else None

                # Add or update student
                if ogrenci_no not in ogrenciler_dict:
                    ogrenciler_dict[ogrenci_no] = {
                        'ogrenci_no': ogrenci_no,
                        'ad_soyad': ad_soyad,
                        'sinif': sinif,
                        'dersler': []
                    }

                # Add course if specified
                if ders and ders != 'nan' and ders != '':
                    ogrenciler_dict[ogrenci_no]['dersler'].append(ders)

            # Convert to list
            ogrenciler = list(ogrenciler_dict.values())

            logger.info(f"✅ {len(ogrenciler)} öğrenci Excel'den yüklendi")
            return ogrenciler

        except Exception as e:
            logger.error(f"Excel parse hatası: {e}")
            raise ValueError(f"Excel dosyası okunamadı: {str(e)}")

    @staticmethod
    def parse_derslik_listesi(file_path: str) -> List[Dict]:
        """
        Parse classroom list from Excel file

        Expected columns:
        - Derslik Kodu
        - Derslik Adı
        - Kapasite
        - Satır Sayısı
        - Sütun Sayısı
        - Sıra Yapısı

        Args:
            file_path: Path to Excel file

        Returns:
            List of classroom dictionaries
        """
        try:
            df = pd.read_excel(file_path)
            df.columns = df.columns.str.strip().str.lower()

            # Remove Turkish characters
            df.columns = df.columns.str.replace('ı', 'i').str.replace('ş', 's').str.replace('ğ', 'g')
            df.columns = df.columns.str.replace('ü', 'u').str.replace('ö', 'o').str.replace('ç', 'c')

            column_mapping = {
                'derslik kodu': 'derslik_kodu',
                'derslik kod': 'derslik_kodu',
                'kod': 'derslik_kodu',
                'derslik adi': 'derslik_adi',
                'derslik ad': 'derslik_adi',
                'ad': 'derslik_adi',
                'adi': 'derslik_adi',
                'kapasite': 'kapasite',
                'satir sayisi': 'satir_sayisi',
                'satir': 'satir_sayisi',
                'sutun sayisi': 'sutun_sayisi',
                'sutun': 'sutun_sayisi',
                'sira yapisi': 'sira_yapisi',
                'sira': 'sira_yapisi'
            }

            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df.rename(columns={old_name: new_name}, inplace=True)

            required = ['derslik_kodu', 'derslik_adi', 'kapasite']
            missing = [col for col in required if col not in df.columns]

            if missing:
                raise ValueError(f"Eksik sütunlar: {', '.join(missing)}")

            derslikler = []
            for _, row in df.iterrows():
                kapasite = int(row['kapasite'])
                derslik = {
                    'derslik_kodu': str(row['derslik_kodu']).strip().upper(),
                    'derslik_adi': str(row['derslik_adi']).strip(),
                    'kapasite': kapasite,
                    'satir_sayisi': int(row.get('satir_sayisi', 10)),
                    'sutun_sayisi': int(row.get('sutun_sayisi', 6)),
                    'sira_yapisi': int(row.get('sira_yapisi', 3))
                }
                derslikler.append(derslik)

            logger.info(f"✅ {len(derslikler)} derslik Excel'den yüklendi")
            return derslikler

        except Exception as e:
            logger.error(f"Excel parse hatası: {e}")
            raise ValueError(f"Excel dosyası okunamadı: {str(e)}")

    @staticmethod
    def validate_excel_file(file_path: str) -> bool:
        """
        Validate Excel file

        Args:
            file_path: Path to Excel file

        Returns:
            True if valid, False otherwise
        """
        try:
            path = Path(file_path)

            if not path.exists():
                return False

            if path.suffix.lower() not in ['.xlsx', '.xls']:
                return False

            pd.read_excel(file_path, nrows=1)

            return True

        except Exception as e:
            logger.error(f"Excel validation error: {e}")
            return False