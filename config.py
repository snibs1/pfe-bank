import os

class Config:
    SECRET_KEY = 'nb_bank_2026_secure_key'
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(BASE_DIR, 'bank_data.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False