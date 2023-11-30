from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect

from database_operations import insert_initial_data
from helpers import list_all_rooms_for, get_hotel_object_from, get_room_types, configure_jinja_environment, get_avaiable_rooms
from models import db, BedTypes, AmenityTypes

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:admin@localhost/Hotel'
db.init_app(app)

configure_jinja_environment(app)

with app.app_context():   
    if not inspect(db.engine).has_table("hotels"):
        db.create_all()
        insert_initial_data(db)
    else:
        #load in data from the database into session
        pass

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/booking", methods=["GET"])
def book():
    from_date = request.args.get("start_date")
    to_date = request.args.get("end_date")
    hotel = get_hotel_object_from(db, "Blue Prints Hotel")

    if not (from_date or to_date):
        rooms = list_all_rooms_for(db, hotel.id)
    else:
        rooms = get_avaiable_rooms(db, hotel.id, from_date, to_date)

    room_types = get_room_types(db, rooms)
    
    bed_types = db.session.query(BedTypes).all()
    bed_types_dict = {bed_type.id: bed_type for bed_type in bed_types}

    amenities = db.session.query(AmenityTypes).all()
    amenities_dict = {amenity.id: amenity for amenity in amenities}

    room_capacities = {}
    for room_type in room_types:
        room_capacity = sum([bed_types_dict[beds.bed_type_id].capacity for beds in room_type.beds])
        room_capacities[room_type.name] = room_capacity

    return render_template("booking.html",
                        room_types=room_types,
                        bed_types=bed_types_dict,
                        amenities=amenities_dict,
                        room_capacities=room_capacities)