import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'selcuk-ceng-topluma-hizmet-gizli-anahtar-2026')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Dosya Yükleme Ayarları
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 Megabyte sınırı
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
