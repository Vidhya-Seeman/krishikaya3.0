from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # landowner, labor, machinery, admin

    # Extra fields for landowner/labor/machinery
    name = db.Column(db.String(100))
    address = db.Column(db.String(200))
    contact = db.Column(db.String(20))
    district = db.Column(db.String(50))
    acres = db.Column(db.Integer)   # For landowner
    crops = db.Column(db.String(200))  # For landowner
    machine_type = db.Column(db.String(50)) # For machinery
    num_labors = db.Column(db.Integer) # For laborers if needed

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    landowner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    service_date = db.Column(db.String(20))
    days = db.Column(db.Integer)
    service_type = db.Column(db.String(20))  # labor, machinery, both
    num_labor = db.Column(db.Integer)
    machine_type = db.Column(db.String(50))
    status = db.Column(db.String(20), default="Pending")

class BookingResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    response = db.Column(db.String(10))  # Accept/Reject
