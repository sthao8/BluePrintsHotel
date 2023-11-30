from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Hotels(db.Model):
    __tablename__ = "hotels"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    post_code = db.Column(db.Integer, nullable=False)

    rooms = db.relationship('Rooms', backref='hotels', lazy=True)

class RoomTypes(db.Model):
    __tablename__ = "room_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(15), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    base_rate_per_night = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    room_size = db.Column(db.Integer, nullable=False)

    rooms = db.relationship("Rooms", backref="room_types", lazy=False)
    amenities = db.relationship("RoomAmenities", backref="room_types", lazy=False)
    beds = db.relationship("RoomBeds", backref="room_types", lazy=False)
    images = db.relationship("Images", backref="room_types", lazy=False)

class Images(db.Model):
    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), nullable=False)
    room_type_id = db.Column(db.Integer, db.ForeignKey("room_types.id"))

class Customers(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    post_code = db.Column(db.Integer, nullable=False)
    country = db.Column(db.String(50), nullable=False)

    bookings = db.relationship("Bookings", backref="customers", lazy=True)

class Rooms(db.Model):
    __tablename__ = "rooms"

    room_number = db.Column(db.Integer, primary_key=True, autoincrement=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"))
    room_type = db.Column(db.Integer, db.ForeignKey("room_types.id"))

    bookings = db.relationship("Bookings", backref="rooms", lazy=True)

class BedTypes(db.Model):
    __tablename__ = "bed_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

    room_beds = db.relationship('RoomBeds', backref='bed_types', lazy=False)

class AmenityTypes(db.Model):
    __tablename__ = "amenity_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255), nullable=False)

class RoomBeds(db.Model):
    __tablename__ = "room_beds"

    id = db.Column(db.Integer, primary_key=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id'))
    bed_type_id = db.Column(db.Integer, db.ForeignKey('bed_types.id'))

class RoomAmenities(db.Model):
    __tablename__ = "room_amenities"

    id = db.Column(db.Integer, primary_key=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id'))
    amenity_type_id = db.Column(db.Integer, db.ForeignKey('amenity_types.id'))

class Bookings(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    room_number = db.Column(db.Integer, db.ForeignKey('rooms.room_number'))
    reservation_date = db.Column(db.Date, default=db.func.current_date())
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    number_of_extra_beds = db.Column(db.Integer, nullable=False)
    cost = db.Column(db.Numeric(precision=10, scale=2), nullable=False)

    invoices = db.relationship("Invoices", backref="bookings", lazy=True)

class Invoices(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"))
    due_date = db.Column(db.Date, nullable=False)

    payment = db.relationship("Payments", backref="invoices", lazy=True)

class Payments(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"))
    payment_date = db.Column(db.Date, nullable=False)
