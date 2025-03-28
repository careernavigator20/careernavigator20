from app import app, db
from model import *

with app.app_context():
    db.drop_all()  # Be careful with this in production!
    db.create_all()
    print("Database tables created successfully!") 