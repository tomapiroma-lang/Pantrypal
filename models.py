from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin # pyright: ignore[reportMissingImports]
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) # ინახავს bcrypt-ით დაშიფრულ ჰეშს
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # კავშირი მომხმარებლის პროდუქტებთან (Pantry)
    pantry_items = db.relationship('PantryItem', backref='owner', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        """ჰეშირებას უკეთებს პაროლს ბაზაში ჩაწერამდე (Bcrypt/Werkzeug-ის დაცვა)"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """ამოწმებს შეყვანილი პაროლის სისწორეს ჰეშთან შედარებით"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class PantryItem(db.Model):
    __tablename__ = 'pantry_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # პროდუქტის სახელი (გადაეცემა Grok API-ს)
    quantity = db.Column(db.String(50), nullable=True) # მაგ: "2 კგ", "5 ცალი"
    expiration_date = db.Column(db.Date, nullable=True) # ვადების კონტროლისთვის
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # უცხო გასაღები მომხმარებელთან დასაკავშირებლად
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def is_expired(self):
        """ამოწმებს პროდუქტს ვადა ხომ არ გაუვიდა"""
        if self.expiration_date:
            return self.expiration_date < datetime.utcnow().date()
        return False

    def __repr__(self):
        return f'<PantryItem {self.name} for User_ID {self.user_id}>'