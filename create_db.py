from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    contact_number = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    con_password = db.Column(db.String(255), nullable=False)
    interests = db.Column(db.Text, nullable=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

