from datetime import date
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect,select

from database_operations import insert_initial_data
from helpers import list_all_rooms_for, to_date_object, get_hotel_object_from, get_room_types, configure_jinja_environment, get_available_rooms, get_count_per_type, to_date_from_session
from models import db, BedTypes, AmenityTypes, RoomTypes, RoomBeds

#TODO: change how we store dates fom js
# ask if they want to accept cost of double rooms if guests > base capacity

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = "BlueprintsHotel"
app.config["SQLALCHEMY_DATABASE_URI"] = 'mysql+mysqlconnector://root:admin@localhost/Hotel'
db.init_app(app)

configure_jinja_environment(app)

with app.app_context():
    if not inspect(db.engine).has_table("hotels"):
        db.create_all()
        insert_initial_data(db)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/select-rates", methods=["GET"])
def select_rates():
    hotel = get_hotel_object_from(db, "Blue Prints Hotel")
    session["hotel_id"] = hotel.id

    # Convert to date, else None
    from_date = to_date_object(request.args.get("start_date"))
    to_date = to_date_object(request.args.get("end_date"))

    try:
        guests = int(request.args.get("people"))
    except TypeError:
        guests = 1

    # Store this info in session so we can retrieve it later
    if from_date and to_date:
        if to_date >= date.today() and to_date > from_date and guests:
            session["booking_details"] =     {
                "selected_from_date": from_date,
                "selected_to_date": to_date,
                "guests": guests
                }
        else:
            flash("Invalid dates selected", "error")
            return redirect("/select-rates")

    # Get available rooms if there are dates provided, else get all rooms for hotel
    if not (from_date or to_date):
        rooms = list_all_rooms_for(db, hotel.id)
    else:
        rooms = get_available_rooms(db, hotel.id, from_date, to_date)

    room_types = get_room_types(db, rooms)
    
    # Check if available rooms can support number of requested guests
    # Calculate number of rooms per type
    room_max_capacity_satisfies_guests = False
    available_rooms_per_type = {}
    for room_type in room_types:
        available_rooms_per_type[room_type.id] = get_count_per_type(room_type.id, rooms)
        if room_type.max_capacity >= guests:
            room_max_capacity_satisfies_guests = True

    bed_types = db.session.query(BedTypes).all()
    bed_types_dict = {bed_type.id: bed_type for bed_type in bed_types}

    amenities = db.session.query(AmenityTypes).all()
    amenities_dict = {amenity.id: amenity for amenity in amenities}

    return render_template("select-rates.html",
                        room_types=room_types,
                        room_available_for_no_of_guests=room_max_capacity_satisfies_guests,
                        available_rooms=available_rooms_per_type,
                        bed_types=bed_types_dict,
                        amenities=amenities_dict,
                        guests=guests)

@app.route("/book", methods=["GET", "POST"])
def book():
    if request.method == "POST":
        selected_room_type_id = request.form.get("room_type_id")
        selected_room:RoomTypes = db.session.query(RoomTypes).filter_by(id=selected_room_type_id).first()

        booking_details = session.get("booking_details")
        to_date = to_date_from_session(booking_details["selected_to_date"])
        from_date = to_date_from_session(booking_details["selected_from_date"])
        nights = (to_date - from_date).days
        booking_details["nights"] = nights

        total_cost = selected_room.base_rate_per_night * nights
        booking_details["total_cost"] = total_cost

        bed_types = db.session.query(
            BedTypes,
            db.func.count().label("bed_count")
        ).join(
            RoomBeds, BedTypes.id==RoomBeds.bed_type_id
        ).filter(
            RoomBeds.room_type_id == selected_room_type_id
        ).group_by(
            BedTypes
        ).all()
        beds = []
        for bed_type, bed_count in bed_types:
            bed = {
                "bed_type": bed_type,
                "bed_count": bed_count
            }
            beds.append(bed)
        return render_template("book.html",
                               selected_room=selected_room,
                               booking_details=booking_details,
                               beds=beds)
    else:
        return redirect("/select-rates")
    
@app.route("/confirmation", methods=["POST"])
def confirmation():
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Check if username given and unique
        username = request.form.get("registerUsername")
        if not username:
            return render_template("error.html", error="Username required.")
        elif username in [
            row["username"] for row in db.execute("SELECT username FROM users;")
        ]:
            return render_template("error.html", error="Username unavailable.")

        # Check if password exists and matches confirmation password
        password = request.form.get("registerPassword")
        confirmation = request.form.get("registerPasswordConfirm")
        if not password and not confirmation:
            return render_template("error.html", error="Password fields required.")
        elif password != confirmation:
            return render_template("error.html", error="Passwords do not match.")


        flash("Registration successful!")
        return redirect("/")
    return render_template("register.html")

@app.route("/login", methods=["GET"])
def login():
    return redirect("/")

@app.route("/pay", methods=["GET", "POST"])
def pay():
    return redirect("/")