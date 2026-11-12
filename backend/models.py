"""SQLAlchemy models (proposal §3.3.3.2). Mirrors db/schema.sql."""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False)  # admin|dispatcher|driver|regulator


class Bin(db.Model):
    __tablename__ = "bins"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, unique=True, nullable=False)
    location_name = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    capacity_litres = db.Column(db.Integer, default=240)
    status = db.Column(db.Text, default="active")

    def latest_telemetry(self):
        return (TelemetryReading.query.filter_by(bin_id=self.id)
                .order_by(TelemetryReading.recorded_at.desc()).first())


class TelemetryReading(db.Model):
    __tablename__ = "telemetry_readings"
    id = db.Column(db.Integer, primary_key=True)
    bin_id = db.Column(db.Integer, db.ForeignKey("bins.id"), nullable=False)
    fill_pct = db.Column(db.Float, nullable=False)
    mass_kg = db.Column(db.Float)
    gas_raw = db.Column(db.Integer)
    recorded_at = db.Column(db.DateTime(timezone=True),
                            default=lambda: datetime.now(timezone.utc))


class SortEvent(db.Model):
    __tablename__ = "sort_events"
    id = db.Column(db.Integer, primary_key=True)
    bin_id = db.Column(db.Integer, db.ForeignKey("bins.id"), nullable=False)
    category = db.Column(db.Text, nullable=False)  # recyclable|organic|general
    recorded_at = db.Column(db.DateTime(timezone=True),
                            default=lambda: datetime.now(timezone.utc))


class CollectionRoute(db.Model):
    __tablename__ = "collection_routes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    total_distance_km = db.Column(db.Float)
    status = db.Column(db.Text, default="planned")


class RouteStop(db.Model):
    __tablename__ = "route_stops"
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("collection_routes.id"), nullable=False)
    bin_id = db.Column(db.Integer, db.ForeignKey("bins.id"), nullable=False)
    stop_order = db.Column(db.Integer, nullable=False)
