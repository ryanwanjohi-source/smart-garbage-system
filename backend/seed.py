"""Seed demo data: 6 Nairobi bins + a dispatcher user. Idempotent.
Run:  DATABASE_URL=... python seed.py
"""
import os
import sys
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(__file__))
from models import db, Bin, User
from flask import Flask

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "postgresql://smartbin:smartbin@localhost:5432/smartbin")
db.init_app(app)

BINS = [
    ("NRB-001", "Kilimani Market",      -1.2921, 36.8219),
    ("NRB-002", "Kenyatta Avenue",      -1.2864, 36.8172),
    ("NRB-003", "Westlands Mall",       -1.2635, 36.8028),
    ("NRB-004", "Ngong Road",           -1.3018, 36.7890),
    ("NRB-005", "Kasarani Stadium",     -1.2197, 36.8963),
    ("NRB-006", "Karen Shopping Centre", -1.3310, 36.7048),
]

with app.app_context():
    db.create_all()
    for code, loc, lat, lng in BINS:
        if not Bin.query.filter_by(code=code).first():
            db.session.add(Bin(code=code, location_name=loc,
                               latitude=lat, longitude=lng))
            print("added", code)
    if not User.query.filter_by(email="dispatcher@demo.ke").first():
        db.session.add(User(
            name="Demo Dispatcher", email="dispatcher@demo.ke",
            password_hash=generate_password_hash("demo1234"),
            role="dispatcher"))
        print("added demo dispatcher (dispatcher@demo.ke / demo1234)")
    db.session.commit()
print("seed done")
