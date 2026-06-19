import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-very-secret-key-12345')
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
    UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY')
    
    # ამ ხაზის დამატებით Warning-ი სამუდამოდ გაქრება:
    SQLALCHEMY_TRACK_MODIFICATIONS = False