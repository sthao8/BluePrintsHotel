import jinja2
import random

from datetime import datetime, date
from flask import flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, desc, asc, and_, or_, not_, except_
from sqlalchemy.orm import joinedload
from typing import List

from models import Rooms, Hotels, RoomTypes, BedTypes, RoomBeds, Bookings, Invoices, Customers


def format_sek(value):
    return '{:,.0f}'.format(float(value)).replace(",", " ").replace(".",",")

def format_date(target_date):
    return target_date.strftime("%d %B %Y")

def date_from_datetime(target_datetime):
    return target_datetime.date()

def configure_jinja_environment(app):
    app.jinja_env.filters['format_sek'] = format_sek
    app.jinja_env.filters['format_date'] = format_date
    app.jinja_env.filters['date_from_datetime'] = date_from_datetime

def list_all_rooms_for(db:SQLAlchemy) -> List[Rooms]:
    room_numbers:List[Rooms] = db.session.execute(
        select(Rooms.room_number)
        ).scalars().all()

    query = select(Rooms).options(
            joinedload(Rooms.room_type).joinedload(RoomTypes.amenities),
            joinedload(Rooms.room_type).joinedload(RoomTypes.beds)
        ).where(Rooms.room_number.in_(room_numbers))

    rooms = db.session.execute(query).unique().scalars().all()

    return rooms

def get_room_types(db:SQLAlchemy, rooms: List[Rooms]):
    query = (db.session.query(RoomTypes)
             .filter(RoomTypes.id.in_(room.room_type_id for room in rooms))
             .distinct()
             .options(
                  joinedload(RoomTypes.beds),
                  joinedload(RoomTypes.amenities)
             ).order_by(desc(RoomTypes.id))
    )
                  
    room_types = query.all()        

    return room_types

def get_hotel_object_from(db, hotel_name):
    return db.session.query(Hotels).filter_by(name=hotel_name).first()

def to_date_object(string_date:str):
    try:
        return datetime.strptime(string_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None

def get_available_rooms(db: SQLAlchemy, requested_checkin_date: date, requested_checkout_date: date) -> List[Rooms]:
    # subq searches for all rooms that have active bookings during date range
    unavailable_rooms_subq = (select(Bookings.room_number)
                              .where(
                                  (requested_checkin_date < Bookings.check_out_date) &
                                  (requested_checkout_date > Bookings.check_in_date) &
                                  (Bookings.status_expression == "Confirmed")
                              )
                              ).alias()
    
    available_rooms = (
        db.session.query(Rooms)
        .filter(
            ~Rooms.room_number.in_(unavailable_rooms_subq))
        .options(joinedload(Rooms.room_type))
        .order_by(Rooms.room_number)
        .all()
    )

    return available_rooms

def assign_random_room(all_available_rooms: List[Rooms], room_type_id) -> Rooms:
    available_rooms = [room for room in all_available_rooms if room.room_type_id == int(room_type_id)]

    # Return a random room if there are any available rooms
    if available_rooms:
        random_room = random.choice([available_rooms])
        return random_room
    else:
        return None

def get_count_per_type(room_type, rooms:List[Rooms]) -> int:
    #TODO maybe combine this with get_availble_rooms select(count(room_type_id)), room_type, group by room_type
    return sum([1 for room in rooms if room.room_type_id == room_type])

def get_customer(db, email, booking_id) -> None|Customers:
    try:
        booking_id = int(booking_id)
    except (TypeError, ValueError):
        booking_id = None
        return None

    if not (email and booking_id):
        return None
  
    customer = db.session.query(Customers).join(Bookings).filter(Customers.email==email, Bookings.id==booking_id).options(joinedload(Customers.bookings)).one_or_none()
    
    if not customer:
        return None
    
    return customer

def get_available_rooms_for_reschedule(db:SQLAlchemy, requested_checkin_date, requested_checkout_date, current_booking_id, no_of_guests):
    # expression for finding all unavailable rooms, excluding current booking
    unavailable_rooms_subq = (select(Bookings.room_number)
                            .where(
                                (requested_checkin_date < Bookings.check_out_date) &
                                (requested_checkout_date > Bookings.check_in_date) &
                                (Bookings.status_expression == "Confirmed") &
                                (Bookings.id != current_booking_id)
                            )
                            ).alias()
    
    rooms = (
        db.session.query(Rooms)
        .filter(
            ~Rooms.room_number.in_(unavailable_rooms_subq))
        .order_by(Rooms.room_number)
        .all()
    )

    #filter in python by capacity
    rooms = [room for room in rooms if room.room_type.max_capacity >= no_of_guests]

    return rooms
    
def calculate_nights(to_date: date, from_date:date):
    return (to_date - from_date).days

def calculate_rate_per_night(base_rate, extra_beds):
    return base_rate + (extra_beds * 200)