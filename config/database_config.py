"""
Database Configuration
Centralized database settings and utilities
"""

import os
from typing import Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig:
    """Database configuration class"""
    
    # Connection settings
    HOST = os.getenv('DB_HOST', 'localhost')
    PORT = int(os.getenv('DB_PORT', 5432))
    DATABASE = os.getenv('DB_NAME', 'sinav_takvimi_db')
    USER = os.getenv('DB_USER', 'postgres')
    PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # Connection pool settings
    POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 5))
    MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', 20))
    
    # Connection timeout
    CONNECT_TIMEOUT = 10
    
    @classmethod
    def get_connection_string(cls) -> str:
        """Get database connection string"""
        return f"postgresql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"
    
    @classmethod
    def get_connection_dict(cls) -> Dict:
        """Get connection parameters as dictionary"""
        return {
            'host': cls.HOST,
            'port': cls.PORT,
            'database': cls.DATABASE,
            'user': cls.USER,
            'password': cls.PASSWORD,
            'connect_timeout': cls.CONNECT_TIMEOUT
        }
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        required_fields = [cls.HOST, cls.DATABASE, cls.USER]
        return all(required_fields)


class AppConfig:
    """Application configuration"""
    
    # Environment
    ENV = os.getenv('APP_ENV', 'production')
    DEBUG = os.getenv('APP_DEBUG', 'False').lower() == 'true'
    LOG_LEVEL = os.getenv('APP_LOG_LEVEL', 'INFO')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
    PASSWORD_MIN_LENGTH = int(os.getenv('PASSWORD_MIN_LENGTH', 8))
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 480))  # minutes
    
    # File upload
    MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', 10 * 1024 * 1024))  # 10MB
    ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS', 'xlsx,xls,pdf').split(',')
    
    # Exam defaults
    DEFAULT_EXAM_DURATION = int(os.getenv('DEFAULT_EXAM_DURATION', 120))  # minutes
    DEFAULT_BREAK_DURATION = int(os.getenv('DEFAULT_BREAK_DURATION', 30))  # minutes
    MAX_EXAMS_PER_DAY = int(os.getenv('MAX_EXAMS_PER_DAY', 3))
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production"""
        return cls.ENV == 'production'
    
    @classmethod
    def is_debug(cls) -> bool:
        """Check if debug mode is enabled"""
        return cls.DEBUG


class EmailConfig:
    """Email configuration (optional)"""
    
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_FROM = os.getenv('SMTP_FROM', 'noreply@kocaeli.edu.tr')
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if email is configured"""
        return bool(cls.SMTP_USER and cls.SMTP_PASSWORD)


# Export configurations
__all__ = ['DatabaseConfig', 'AppConfig', 'EmailConfig']
