import jinja2

from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, desc, asc, and_, or_, not_
from sqlalchemy.orm import joinedload
from typing import List


from models import Rooms, Hotels, RoomTypes, BedTypes, RoomBeds, Bookings


def format_sek(value):
    return '{:,.2f}'.format(float(value)).replace(",", " ").replace(".",",")

def configure_jinja_environment(app):
    app.jinja_env.filters['format_sek'] = format_sek

def list_all_rooms_for(db:SQLAlchemy, target_hotel_id) -> List[Rooms]:
    room_numbers:List[Rooms] = db.session.execute(
        select(Rooms.room_number)
        .where(Rooms.hotel_id==target_hotel_id)).scalars().all()

    query = select(Rooms).options(
            joinedload(Rooms.room_types).joinedload(RoomTypes.amenities),
            joinedload(Rooms.room_types).joinedload(RoomTypes.beds),
            joinedload(Rooms.room_types).joinedload(RoomTypes.images)
        ).where(Rooms.room_number.in_(room_numbers))

    rooms = db.session.execute(query).unique().scalars().all()

    return rooms

def get_room_types(db:SQLAlchemy, rooms: List[Rooms]):
    query = (db.session.query(RoomTypes)
             .filter(RoomTypes.id.in_(room.room_type for room in rooms))
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
        return datetime.strptime(string_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    
def to_date_from_session(string_date:str):
    try:
        return datetime.strptime(string_date, "%a, %d %b %Y %H:%M:%S GMT")
    except (ValueError, TypeError):
        return None

def get_available_rooms(db: SQLAlchemy, target_hotel_id:int, requested_checkin_date: date, requested_checkout_date: date):
    subq = (
        select(1)
        .where(and_(
            Bookings.room_number == Rooms.room_number,
            requested_checkin_date < Bookings.check_out_date,
            requested_checkout_date > Bookings.check_in_date
        ))
    )

    available_rooms = (
        db.session.query(Rooms)
        .filter(and_(
            ~subq.exists(),
            Rooms.hotel_id==target_hotel_id))
        .all()
    )
    
    return available_rooms
    
def get_count_per_type(room_type, rooms:List[Rooms]) -> int:
    return sum([1 for room in rooms if room.room_type == room_type])