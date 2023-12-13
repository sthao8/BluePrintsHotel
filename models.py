from datetime import date, datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import not_
import math

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

class UserAccounts(db.Model):
    __tablename__ = "user_accounts"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(180), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    # customers = db.relationship("Customers", backref="user_accounts", lazy=False)

class Customers(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    # user_account_id = db.Column(db.Integer, db.ForeignKey("user_accounts.id"), nullable=True)

    bookings = db.relationship("Bookings", backref="customer", lazy=False)

class RoomTypes(db.Model):
    __tablename__ = "room_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(15), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    base_rate_per_night = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    room_size = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)

    # rooms = db.relationship("Rooms", backref="room_types", lazy=False)
    amenities = db.relationship("RoomAmenities", backref="room_type", lazy=False)
    beds = db.relationship("RoomBeds", backref="room_type", lazy=False)

    @property
    def base_capacity(self) -> int:
        bed_types = db.session.query(BedTypes).all()
        bed_types_dict = {bed_type.id: bed_type for bed_type in bed_types}
        return sum(bed_types_dict[bed_type.bed_type_id].capacity for bed_type in self.beds)

    @property
    def max_extra_beds(self) -> int:
        extra_bed_space_required = 6
        base_sizes = {
            "Luxe double": 25,
            "Standard double": 18,
            "Standard single": 14
        }
        return max(0, math.floor((self.room_size - base_sizes[self.name]) / extra_bed_space_required))

    @property
    def max_capacity(self) -> int:
        return self.base_capacity + self.max_extra_beds

class Rooms(db.Model):
    __tablename__ = "rooms"

    room_number = db.Column(db.Integer, primary_key=True, autoincrement=False)
    room_type_id = db.Column(db.Integer, db.ForeignKey("room_types.id"))

    bookings = db.relationship("Bookings", backref="room", lazy="joined", uselist=True)
    room_type = db.relationship("RoomTypes", backref="rooms", lazy=False, uselist=False)

class BedTypes(db.Model):
    __tablename__ = "bed_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

class RoomBeds(db.Model):
    __tablename__ = "room_beds"

    id = db.Column(db.Integer, primary_key=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id'))
    bed_type_id = db.Column(db.Integer, db.ForeignKey('bed_types.id'))

    bed_type = db.relationship("BedTypes", backref="room_bed", lazy="joined", uselist=False)

class AmenityTypes(db.Model):
    __tablename__ = "amenity_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255), nullable=False)

class RoomAmenities(db.Model):
    __tablename__ = "room_amenities"

    id = db.Column(db.Integer, primary_key=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id'))
    amenity_type_id = db.Column(db.Integer, db.ForeignKey('amenity_types.id'))

    amenity_type = db.relationship("AmenityTypes", backref="room_amenity", lazy="joined")

class Invoices(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    due_date = db.Column(db.Date, nullable=True)
    payment_timestamp = db.Column(db.DateTime, default=None)
    payment_amount = db.Column(db.Numeric(10, 2), default=None)
    void_date = db.Column(db.Date, nullable=True)

    @hybrid_property
    def status(self) -> str:
        if not self.void_date:
            if self.payment_timestamp:
                return "Paid"
            # hasn't been canceled and past the due date
            elif date.today() > self.due_date:
                return "Overdue"
            else:
                return "Issued"
        else:
            if not self.payment_timestamp:
                return "Voided"
            else:
                return "Refunded"
        
        
    @status.expression
    def status_expression(cls):
        return db.case(
            (db.and_(cls.void_date.is_(None), cls.payment_timestamp.isnot(None)), "Paid"),
            (db.and_(cls.void_date.is_(None), cls.payment_timestamp.is_(None), date.today() > cls.due_date), "Overdue"),
            (db.and_(cls.void_date.is_(None), cls.payment_timestamp.is_(None), date.today() < cls.due_date), "Issued"),
            (db.and_(cls.void_date.isnot(None), cls.payment_timestamp.is_(None)), "Voided"),
            (db.and_(cls.void_date.isnot(None), cls.payment_timestamp.isnot(None)), "Refunded"),
            else_="None")
        
class CancellationCodes(db.Model):
    __tablename__ = "cancellation_codes"

    code = db.Column(db.String(3), primary_key=True, autoincrement=False, nullable=False)
    description = db.Column(db.String(50), nullable=False)


class Bookings(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    room_number = db.Column(db.Integer, db.ForeignKey('rooms.room_number'), nullable=False)
    reservation_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now())
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    number_of_extra_beds = db.Column(db.Integer, nullable=False)
    cost = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"))
    cancellation_timestamp = db.Column(db.DateTime, default=None, nullable=True)
    cancellation_code = db.Column(db.String(3), db.ForeignKey('cancellation_codes.code'), nullable=True)

    invoice = db.relationship("Invoices", backref="booking", lazy="joined", uselist=False)
    cancellation_reason = db.relationship("CancellationCodes", backref="booking", lazy="joined", uselist=False)

    @property
    def nights(self):
        return (self.check_out_date - self.check_in_date).days

    @property
    def rate_per_night(self):
        return self.room.room_type.base_rate_per_night + (self.number_of_extra_beds * 200)

    @hybrid_property
    def status(self) -> str:
        if self.invoice_id is None:
            return None
        elif self.invoice.status in ("Expired", "Voided", "Refunded"):
            return "Canceled"
        elif date.today() >= self.check_in_date and self.invoice.payment_timestamp:
            return "Completed"
        elif date.today() >= self.check_in_date and not self.invoice.payment_timestamp:
            return "Unpaid"
        else:
            return "Confirmed"

    @status.inplace.expression
    def status_expression(cls):
        return db.case(
            (cls.invoice_id.is_(None), None),
            (db.session.query(Invoices.status_expression)
             .filter_by(id=cls.id)
             .as_scalar().in_(("Expired", "Voided", "Refunded")),
             "Canceled"),
            (db.and_(date.today() >= cls.check_in_date,
             db.session.query(Invoices.payment_timestamp).filter_by(id=cls.id).as_scalar()),
             "Completed"),
            (db.and_(date.today() >= cls.check_in_date,
             not_(db.session.query(Invoices.payment_timestamp).filter_by(id=cls.id).as_scalar())),
             "Unpaid"),
            else_="Confirmed")
    
    def cancel_booking_due_to(self, cancellation_code: str):
        """
        Supported cancellation codes: 'CAN', 'RES', 'NOP'
        """
        if cancellation_code not in ["CAN", "RES", "NOP"]:
            raise ValueError("No such cancellation reason")
        elif (cancellation_code == "NOP"
              and not (self.check_in_date > date.today() > self.invoice.due_date
                       and not self.invoice.payment_timestamp)):
            # Don't actually unbook unless no payment and date after due date and before check in date
            pass
        else:
            self.invoice.void_date = date.today()
            self.cancellation_timestamp = datetime.now()
            self.cancellation_code = cancellation_code
            db.session.commit()

