from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(300), nullable=False)

    def set_password(self, password_to_set):
        self.password = generate_password_hash(password_to_set)

    def check_password(self, password_to_check):
        return check_password_hash(self.password, password_to_check)
