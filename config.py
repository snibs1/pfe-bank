import os

class Config:
    # مفتاح الأمان (ضروري للـ Sessions و Flash messages)
    SECRET_KEY = 'nb_bank_2026_secure_key'
    
    # تحديد مسار المشروع باش نلقاو الداتابيز والموديلات بسهولة
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # رابط قاعدة البيانات (SQLite)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'bank_data.db')
    
    # تعطيل خاصية التتبع (باش ما يتقالش السيت)
    SQLALCHEMY_TRACK_MODIFICATIONS = False