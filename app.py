from datetime import date, datetime, timedelta
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, select, delete
from sqlalchemy.orm import joinedload
from typing import List

from werkzeug.security import check_password_hash, generate_password_hash

from database_operations import insert_initial_data, insert_test_data
from helpers import (
    get_hotel_object_from,
    list_all_rooms_for,
    to_date_object,
    get_room_types,
    configure_jinja_environment,
    get_available_rooms,
    get_count_per_type,
    assign_random_room,
    get_customer,
    get_available_rooms_for_reschedule,
    calculate_nights,
    calculate_rate_per_night
    )
from models import (db,
                    BedTypes,
                    AmenityTypes,
                    RoomTypes,
                    RoomBeds,
                    UserAccounts,
                    Invoices,
                    Bookings,
                    Hotels,
                    Customers,
                    Rooms,
                    CancellationCodes
                    )

import re

#TODO it is dangerous to refresh confirm page
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
        insert_test_data(db)

    # booking = db.session.query(Bookings).filter_by(id=1).options(joinedload(Bookings.invoice)).one()
    # print(booking.nights, booking.rate_per_night)
    # print([bed.bed_type.capacity for bed in booking.room.room_type.beds])
    

@app.route("/", methods=["GET"])
def index():
    hotel = db.session.query(Hotels).one()
    return render_template("index.html", hotel=hotel)

@app.route("/select-rates", methods=["GET"])
def select_rates():
    #clear customer_id in session if exists
    session.pop("customer_id", None)

    # Convert to date, else None
    from_date = to_date_object(request.args.get("start_date"))
    to_date = to_date_object(request.args.get("end_date"))

    try:
        guests = int(request.args.get("people"))
    except TypeError:
        guests = 1

    # Store this info in session so we can retrieve it later
    session["booking_details"] = {}
    if from_date and to_date:
        if from_date.date() >= date.today() and to_date.date() > from_date.date() and guests:
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
        rooms = list_all_rooms_for(db)
    else:
        rooms = get_available_rooms(db, from_date, to_date)

    room_types = get_room_types(db, rooms)
    
    # Check if available rooms can support number of requested guests
    # Calculate number of rooms per type
    room_max_capacity_satisfies_guests = False
    available_rooms_per_type = {}
    for room_type in room_types:
        available_rooms_per_type[room_type.id] = get_count_per_type(room_type.id, rooms)
        if room_type.max_capacity >= guests:
            room_max_capacity_satisfies_guests = True
            extra_beds = guests - room_type.base_capacity
            session["booking_details"]["extra_beds"] =  extra_beds if extra_beds > 0 else 0

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
        selected_room_type: RoomTypes = db.session.query(RoomTypes).filter_by(id=selected_room_type_id).first()

        booking_details = session.get("booking_details")
        booking_details["room_type_id"] = selected_room_type_id

        to_date = booking_details["selected_to_date"].date()
        from_date = booking_details["selected_from_date"].date()

        nights = calculate_nights(to_date, from_date)
        booking_details["nights"] = nights

        # Calculate rates
        rate_per_night = calculate_rate_per_night(selected_room_type.base_rate_per_night, booking_details["extra_beds"])
        total_cost = rate_per_night* nights
        booking_details["rate_per_night"] = rate_per_night
        booking_details["total_cost"] = total_cost

        session["booking_details"] = booking_details

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
                            selected_room=selected_room_type,
                            booking_details=booking_details,
                            beds=beds,
                            customer=None
                            )
    else:
        return redirect("/select-rates")
    
# TODO: refreshes on this page are dangerous
@app.route("/process-booking", methods=["POST"])
def process_booking():
    booking_details = session.get("booking_details")

    try:
        customer_id = session.get("customer_id")
        customer = db.session.query(Customers).filter_by(id=customer_id).one_or_none()
    except (TypeError, ValueError):
        customer = None
    if not customer:
        customer_details_fields = {
            "first name": "first_name",
            "last name": "last_name",
            "country": "country",
            "email": "email",
            "phone number": "phone_number"
            }
        
        for detail_name, detail in customer_details_fields.items():
            if not request.form.get(detail):
                flash(f"Missing required field: {detail_name}","error")
        else:
            customer_details = {value: request.form.get(value) for value in customer_details_fields.values()}
            customer = Customers(**customer_details)

            db.session.add(customer)
            db.session.commit()

    # if room doesn't exist in session, then assign new one
    try:
        room_number = booking_details["room_number"]
        room = db.session.query(Rooms).filter_by(room_number=room_number)
    except KeyError:
        room_number = None
    if not room_number:
        rooms:List[Rooms] = get_available_rooms(
            db,
            booking_details["selected_from_date"],
            booking_details["selected_to_date"]
        )

        room = assign_random_room(rooms, booking_details["room_type_id"])
        room_number = room.room_number

    # either way, make sure room still available when trying to book
    if not room:
        flash("Rooms no longer available", "error")
        return redirect("/select-rates")

    invoice = Invoices(
        due_date = (datetime.today() + timedelta(days=10)).date()
        )

    db.session.add(invoice)
    db.session.commit()

    booking = Bookings(
        customer_id=customer.id,
        room_number=room_number,
        check_in_date=booking_details["selected_from_date"],
        check_out_date=booking_details["selected_to_date"],
        guests=booking_details["guests"],
        number_of_extra_beds=booking_details["extra_beds"],
        cost=booking_details["total_cost"],
        invoice_id=invoice.id
        )
    
    db.session.add(booking)
    db.session.commit()
    
    session.pop("booking_details", None)
    session.pop("customer_id", None)

    return redirect(url_for("confirmation", booking_id=booking.id))

    
@app.route("/confirmation/<booking_id>", methods=["GET"])
def confirmation(booking_id):
    booking = db.session.query(Bookings).filter_by(id=booking_id).options(joinedload(Bookings.invoice)).one()
    invoice = booking.invoice
    customer = db.session.query(Customers).filter_by(id=booking.customer_id).one()

    return render_template(
            "confirmation.html",
            customer=customer,
            booking=booking,
            invoice=invoice
            )

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # ask for email address, and include checks
        email = request.form.get("register_email")
        
        if not email:
            flash("Please enter email address", "error")
            return redirect("/register")
        elif re.fullmatch(r"[^@]+@\S+\.\S+", email) is None:
            flash ("Improper mail address", "error")
            return redirect("/register")
        elif email in [
            account.email for account in db.session.query(UserAccounts).all()
        ]:
            flash("Email address already associated with existing account", "error")
            return redirect("/register")
        
        # Check if password exists and matches confirmation password
        password = request.form.get("register_password")
        confirmation = request.form.get("register_password_confirm")
        if not password and not confirmation:
            flash("Password fields required", "error")
            return redirect("/register")
        elif password != confirmation:
            flash("Passwords do not match", "error")
            return redirect("/register")

        # Insert new user into database
        new_user: UserAccounts = UserAccounts(email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in with your new account", "info")
        return redirect("/")
    return render_template("register.html")

@app.route("/login", methods=["POST"])
def login():
    session.pop("user_id", None)

    # makes sure both fields were given
    if not request.form.get("username"):
        return render_template("error.html", error="Username required.")
    elif not request.form.get("password"):
        return render_template("error.html", error="Password required.")

    # validates email and password
    user = db.session.query(UserAccounts).filter_by(email=request.form.get("username")).first()

    if not user or not check_password_hash(
        user.password, request.form.get("password")
    ):
        flash("Invalid username or password", "error")
        return redirect("/")

    # Remembers which user is logged into session
    session["user_id"] = user.id

    # Special status for admin
    session["is_admin"] = user.is_admin

    flash(f"Welcome back, {user.email}!", "info")
    return redirect("/")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    flash("Logout successful.","info")
    return redirect("/")

@app.route("/delete-account", methods=["GET", "POST"])
def delete_account():
    if request.method == "POST":
        email = request.form.get("email")
        #check if customer exists in db
        customers = db.session.query(Customers).filter_by(email=email).distinct().all()
        if not customers:
            flash("No customer found!")
            return redirect("/delete-account")
        
        #check if active bookings exist for email
        bookings = db.session.query(Bookings).join(Customers).filter(Customers.email==email, Bookings.status_expression.in_(["Confirmed", "Unpaid"])).all()
        if len(bookings) > 0:
            flash("Cannot delete. User has active bookings.")
            return redirect("/delete-account")
            
        #then delete the customer(aka set values to null)
        for customer in customers:
            customer.country = None
            customer.email = None
            customer.first_name = None
            customer.last_name = None
            customer.phone_number = None
        db.session.commit()

        flash("Customer deleted")
        return redirect("/delete-account")
    return render_template("delete-customer.html")

@app.route("/my-account", methods=["GET", "POST"])
def my_account():
    return render_template("myaccount.html")

@app.route("/change-booking", methods=["GET"])
def change_booking():
    
    # get and validate email and booking id if exists, else None
    email = request.args.get("email")
    try:
        booking_id = int(request.args.get("booking_id"))
    except (TypeError, ValueError):
        booking_id = None

    # couldn't validate one of these in terms of right format
    if (email and not booking_id) or (not email and booking_id):
        flash("Booking not found!")
        return redirect("/reschedule")
    
    # get new dates and guests
    from_date = to_date_object(request.args.get("start_date"))
    to_date = to_date_object(request.args.get("end_date"))
    try:
        guests = int(request.args.get("people"))
    except TypeError:
        guests = 1

    # Store this info in session so we can retrieve it later
    # session["booking_details"] = {}
    if from_date and to_date and guests:
        info_entered = True
        if not (from_date.date() >= date.today()
            and to_date.date() > from_date.date()):
            flash("Invalid dates selected", "error")
            return redirect("/reschedule")

        session["booking_details"] =     {
                "selected_from_date": from_date,
                "selected_to_date": to_date,
                "guests": guests,
                }
    else:
        info_entered = False
        rooms = None

    if email and booking_id:
        customer = get_customer(db, email, booking_id)
        if not customer:
            # fields entered with wrong info
            flash("Booking not found!", "error")
            return redirect("/reschedule")
        session["booking_details"]["booking_id"] = booking_id
        session["customer_id"] = customer.id
    
    if email and booking_id and from_date and to_date and guests:
        rooms = get_available_rooms_for_reschedule(
            db,
            from_date,
            to_date,
            booking_id,
            guests
        )
    elif from_date and to_date and guests and not (email and booking_id):
        rooms = get_available_rooms(db, from_date, to_date)
        # filter by guests
        rooms = [room for room in rooms if room.room_type.max_capacity >= guests]
        rooms = rooms if len(rooms) > 0 else None

    return render_template(
        "find-booking2.html",
        rooms=rooms,
        guests=guests,
        info_entered=info_entered)


@app.route("/reschedule", methods=["GET", "POST"])
def reschedule():
    if request.method == "POST":
        booking_details = session.get("booking_details")

        room_number = request.form.get("room_id")
        session["booking_details"]["room_number"] = room_number
        
        room = db.session.query(Rooms).filter_by(room_number=room_number).options(joinedload(Rooms.room_type)).one()
        guests = booking_details["guests"]
        extra_beds = guests - room.room_type.base_capacity if guests > 2 else 0
        session["booking_details"]["extra_beds"] =  extra_beds

        nights = calculate_nights(booking_details["selected_to_date"], booking_details["selected_from_date"])
        rate_per_night = calculate_rate_per_night(room.room_type.base_rate_per_night, extra_beds)
        total_cost = rate_per_night * nights
        booking_details["nights"] = nights
        booking_details["rate_per_night"] = rate_per_night
        booking_details["total_cost"] = total_cost

        customer_id = session.get("customer_id", None)
        if customer_id:
            customer = db.session.query(Customers).filter_by(id=customer_id).one()
        else:
            customer = None

        session["booking_details"] = booking_details

        bed_types = db.session.query(
            BedTypes,
            db.func.count().label("bed_count")
        ).join(
            RoomBeds, BedTypes.id==RoomBeds.bed_type_id
        ).filter(
            RoomBeds.room_type_id==room.room_type_id
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

        if customer and booking_details["booking_id"]:
            old_booking = db.session.query(Bookings).filter_by(id=booking_details["booking_id"]).one()
            old_booking.cancel_booking_due_to("RES")
        
        return render_template("book.html",
                               selected_room=room.room_type,
                               booking_details=booking_details,
                               beds=beds,
                               customer=customer
                               )
    return render_template("find-booking2.html")

@app.route("/clear-bookings", methods=["GET", "POST"])
def clear_bookings():
    if request.method == "POST":
        expired_bookings = (
            db.session.query(Bookings)
            .join(Invoices)
            .filter(
                Invoices.due_date < date.today(),
                Invoices.payment_timestamp.is_(None),
                Bookings.cancellation_timestamp.is_(None),
                Bookings.check_in_date > date.today()
            ).all()
        )
        for booking in expired_bookings:
            booking.cancel_booking_due_to("NOP")
        number_of_expired_bookings = len(expired_bookings)
        if number_of_expired_bookings > 0:
            flash(f"{number_of_expired_bookings} booking(s) cleared", "info")
        else:
            flash("No unpaid bookings to clear", "info")
        return redirect("/clear-bookings")
    return render_template("clear-bookings.html")

@app.route("/cancel-reservation", methods=["POST"])
def cancel():
    customer = db.session.query(Customers).filter_by(id=session.get("customer_id")).one()
    if not customer:
        session["to_flash"] = "No customer found"
        return redirect("/find-booking")
    booking = db.session.query(Bookings).filter_by(id=session.get("booking_id")).one()
    
    if booking.status == "Confirmed":
        # booking.cancel_booking_by_customer()
        booking.cancel_booking_due_to("CAN")
        db.session.commit()
        session["to_flash"] = "Booking cancelled"
        return redirect("/find-booking")
    else:
        session["to_flash"] = "Error: cannot cancel booking"
        return redirect("/find-booking")

@app.route("/contact-changed", methods=["POST"])
def confirm_contact_changed():
    customer_details_fields = {
            "first name": "first_name",
            "last name": "last_name",
            "country": "country",
            "phone number": "phone_number"
            }
        
    for detail_name, detail in customer_details_fields.items():
        if not request.form.get(detail):
            session["to_flash"] = f"Missing required field: {detail_name}"
            return redirect("/find-booking")

    customer_id = session.get("customer_id")
    customer = db.session.query(Customers).filter_by(id=customer_id).one()

    customer_details = {value: request.form.get(value) for value in customer_details_fields.values()}
    changes_made = False
    for attribute, value in customer_details.items():
        if getattr(customer, attribute) != value:
            setattr(customer, attribute, value)
            changes_made = True
    db.session.commit()

    if changes_made:
        session["to_flash"] = "Contact info updated"
    else:
        session["to_flash"] = "No changes made to contact info"
    return redirect("/find-booking")

@app.route("/payment-confirmation", methods=["POST"])
def pay_confirmation():
    booking = db.session.query(Bookings).filter_by(id=session.get("booking_id")).options(joinedload(Bookings.invoice)).one()
    invoice = booking.invoice
    payment_made = False
    
    # Only pay if there are no payments already made
    if not invoice.payment_timestamp:
        invoice.payment_timestamp = datetime.now()
        invoice.payment_amount = booking.cost
        db.session.commit()
        payment_made = True
    
    return render_template("pay-confirmation.html", invoice=invoice, payment_made=payment_made)

@app.route("/find-booking", methods=["GET", "POST"])
def find_booking():
    if request.method == "POST":
        # retreive and flash saved messages in session
        message = session.pop("to_flash", None)
        if message:
            flash(message, "info")

        # get customer and booking from session if exists
        try:
            customer = db.session.query(Customers).filter_by(id=session.get("customer_id")).options(joinedload(Customers.bookings)).one_or_none()
            booking = db.session.query(Bookings).filter_by(id=session.get("booking_id"), customer_id=customer.id).options(joinedload(Bookings.invoice)).one_or_none()
        except (KeyError, AttributeError):
            customer = None
            booking = None
        
        # else get customer and booking from form
        if not (customer and booking):
            email = request.form.get("email")
            try:
                booking_id = int(request.form.get("booking_id"))
            except (TypeError, ValueError):
                flash("No bookings found")
                return redirect("/find-booking")

            customer = get_customer(db, email, booking_id)
            if not customer:
                flash("No bookings found")
                return redirect("/find-booking")

            booking = db.session.query(Bookings).filter_by(id=booking_id, customer_id=customer.id).options(joinedload(Bookings.invoice), joinedload(Bookings.cancellation_reason)).one_or_none()
            if not booking:
                flash("No bookings found")
                return redirect("find-booking")
        
            session["customer_id"] = customer.id
            session["booking_id"] = booking_id
            session["booking_logged_in"] = True

        room = db.session.query(Rooms).filter_by(room_number=booking.room_number).options(joinedload(Rooms.room_type)).one()
        
        bed_types = db.session.query(
            BedTypes,
            db.func.count().label("bed_count")
        ).join(
            RoomBeds, BedTypes.id==RoomBeds.bed_type_id
        ).filter(
            RoomBeds.room_type_id==room.room_type_id
        ).group_by(
            BedTypes.id
        ).all()

        beds = []

        for bed_type, bed_count in bed_types:
            bed = {
                "bed_type": bed_type,
                "bed_count": bed_count
            }
            beds.append(bed)

        hotel = get_hotel_object_from(db, "Blue Prints Hotel")

        cancellation_code = db.session.query(CancellationCodes).filter_by(code=booking.cancellation_code).one_or_none()

        return render_template("booking-status.html",
                                customer=customer,
                                room=room,
                                booking=booking,
                                hotel=hotel,
                                cancellation_code=cancellation_code,
                                beds=beds
                                )
    
    return render_template("find-booking.html")