import datetime
import random
import os

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import get_available_rooms

from models import (Hotels,
                    RoomTypes,
                    RoomBeds,
                    Rooms,
                    BedTypes,
                    AmenityTypes,
                    RoomAmenities,
                    UserAccounts,
                    CancellationCodes,
                    Bookings,
                    Invoices,
                    Customers)


def get_images_in_folder(path):
    image_extensions = [".jpg", ".jpeg"]
    image_files = []

    for file in os.listdir(path):
        if (os.path.isfile(os.path.join(path, file))
            and any(file.lower().endswith(ext)) for ext in image_extensions):
            image_files.append(os.path.join(path, file))

    return image_files

def insert_initial_data(database):
    blueprint_hotel = Hotels(
            name="Blue Prints Hotel",
            phone_number="123-456-789",
            email="inquiries@blueprintshotel.com",
            address="Hotellgatan 123",
            city="Västerås",
            country="Sweden",
            post_code=72345,
            )

    database.session.add(blueprint_hotel)

    hairdryer = AmenityTypes(name="Hairdryer", description="Wall-attached hairdryer located in unit's bathroom")
    tv = AmenityTypes(name="TV", description="Flat-screen TV with pay-per-view options")
    minifridge = AmenityTypes(name="Minifridge", description="Minifridge with provided minibar")
    safe = AmenityTypes(name="Security Safe", description="Safety lock box located in entrance closet")
    shower = AmenityTypes(name="Shower", description="Smaller in-unit bathroom with shower")
    bathtub = AmenityTypes(name="Bathtub", description="Larger in-unit bathroom with a bathtub and showerhead")
    database.session.add_all([hairdryer, tv, minifridge, safe, shower, bathtub])

    single_bed = BedTypes(name="Single bed", capacity=1)
    double_bed = BedTypes(name="Double bed", capacity=2)
    database.session.add_all([single_bed, double_bed])

    luxe_double = RoomTypes(
        name="Luxe double",
        description="These luxurious corner rooms feature larger bathrooms and a seating area with a view.",
        base_rate_per_night = 1500,
        room_size = 40,
        image_url = "static/room_images/standard_double2.jpg"
        )
    
    standard_single = RoomTypes(
        name="Standard single",
        description="These simple no-frills rooms are perfect for single travelers on short-stay visits.",
        base_rate_per_night = 900,
        room_size = 15,
        image_url = "static/room_images/standard_double1.jpg"
        )

    standard_double = RoomTypes(
        name="Standard double",
        description="These double rooms offer great quality per price!",
        base_rate_per_night=1000,
        room_size = 25,
        image_url = "static/room_images/luxe_double2.jpg"
        )
    database.session.add_all([luxe_double, standard_double, standard_single])
    database.session.commit()

    room_beds = {
        standard_single.id: [single_bed],
        standard_double.id: [single_bed, single_bed],
        luxe_double.id: [double_bed]
    }

    for id, beds in room_beds.items():
        for bed in beds:
            add_bed = RoomBeds(room_type_id=id,bed_type_id=bed.id)
            database.session.add(add_bed)

    room_amenities = {
        standard_single.id: [tv, minifridge, safe, shower],
        standard_double.id: [tv, minifridge, safe, shower],
        luxe_double.id: [tv, minifridge, safe, bathtub]
    }

    for id, amenities in room_amenities.items():
        for amenity in amenities:
            add_amenity = RoomAmenities(room_type_id=id, amenity_type_id=amenity.id)
            database.session.add(add_amenity)

    room_101 = Rooms(
        room_number=101,
        room_type_id=luxe_double.id,
        )
    room_102 = Rooms(
        room_number=102,
        room_type_id=standard_single.id,
        )
    room_103 = Rooms(
        room_number=103,
        room_type_id=standard_double.id,
        )
    room_104 = Rooms(
        room_number=104,
        room_type_id=standard_single.id,
        )
    room_105 = Rooms(
        room_number=105,
        room_type_id=standard_single.id,
        )
    
    room_201 = Rooms(
        room_number=201,
        room_type_id=luxe_double.id,
        )
    room_202 = Rooms(
        room_number=202,
        room_type_id=standard_single.id,
        )
    room_203 = Rooms(
        room_number=203,
        room_type_id=standard_double.id,
        )
    room_204 = Rooms(
        room_number=204,
        room_type_id=standard_single.id,
        )
    room_205 = Rooms(
        room_number=205,
        room_type_id=standard_single.id,
        )
    
    rooms = [room_101, room_102, room_103, room_104, room_105, room_201, room_202, room_203, room_204, room_205]
    database.session.add_all(rooms)

    admin_account:UserAccounts = UserAccounts(email="admin", password=generate_password_hash("admin"), is_admin=True)
    database.session.add(admin_account)

    cancelled_by_customer = CancellationCodes(code="CAN", description="Cancelled by customer")
    non_payment = CancellationCodes(code="NOP", description="Auto unbooked due to non-payment of invoice")
    rescheduled = CancellationCodes(code="RES", description="Rescheduled")
    database.session.add_all([cancelled_by_customer, non_payment, rescheduled])
    database.session.commit()

def insert_test_data(database):
    customer_infos = [
        {
            "first_name": "Mary",
            "last_name": "Sue",
            "email": "m.sue@mail.com",
            "phone_number": "+1-612-342-1234",
            "country": "USA"
        },
        {
            "first_name": "Nils",
            "last_name": "Nilsson",
            "email": "n.nilsson@mail.com",
            "phone_number": "+46-123 123 322",
            "country": "Sweden" 
        },
        {
            "first_name": "Mai",
            "last_name": "Kit",
            "email": "m.kit@mail.com",
            "phone_number": "+81-123-1231",
            "country": "Japan"
        },
        {
            "first_name": "Sonny",
            "last_name": "Liu",
            "email": "s.liu@mail.com",
            "phone_number": "+852-3234-534",
            "country": "Hong Kong"
        },
        {
            "first_name": "Ben",
            "last_name": "Wilson",
            "email": "b.wilson@mail.com",
            "phone_number": "+1-213-1234",
            "country": "Canada"
        }
    ]

    invoice_infos = [
        {
            "due_date": None,
            "payment_timestamp": None,
            "void_date": None,
        },
        {
            "due_date": None,
            "payment_timestamp": None,
            "void_date": None,
        },
        {
            "due_date": None,
            "payment_timestamp": None,
            "void_date": None,
        },
        {
            "due_date": None,
            "payment_timestamp": None,
            "void_date": None,
        },
        {
            "due_date": None,
            "payment_timestamp": None,
            "void_date": None,
        }
    ]

    # set this dynamically so there's always two bookings to clear when we restart the database
    reservation_timestamp = (datetime.datetime.now() - datetime.timedelta(days=11)).date()
    
    booking_infos = [
        {
            "customer_id": None,
            "room_number": None,
            "reservation_timestamp": datetime.date(2023,12,11),
            "check_in_date": datetime.date(2023,12,13),
            "check_out_date": datetime.date(2023,12,18),
            "guests": 4,
            "number_of_extra_beds": None,
            "cost": None,
            "invoice_id": None,
        },
        {
            # unbook this customer and delete
            "customer_id": None,
            "room_number": None,
            "reservation_timestamp": reservation_timestamp,
            "check_in_date": reservation_timestamp + datetime.timedelta(days=12),
            "check_out_date": reservation_timestamp + datetime.timedelta(days=15),
            "guests": 3,
            "number_of_extra_beds": None,
            "cost": None,
            "invoice_id": None,
        },
        {
            # this one should return unpaid, cannot delete
            "customer_id": None,
            "room_number": None,
            "reservation_timestamp": reservation_timestamp,
            "check_in_date": reservation_timestamp + datetime.timedelta(days=3),
            "check_out_date": reservation_timestamp + datetime.timedelta(days=6),
            "guests": 2,
            "number_of_extra_beds": None,
            "cost": None,
            "invoice_id": None,
        },
        {
            "customer_id": None,
            "room_number": None,
            "reservation_timestamp": datetime.date(2023,12,10),
            "check_in_date": datetime.date(2023,12,12),
            "check_out_date": datetime.date(2023,12,15),
            "guests": 1,
            "number_of_extra_beds": None,
            "cost": None,
            "invoice_id": None,
        }, 
        {
            # this one should be able to be deleted since his is completed and paid
            "customer_id": None,
            "room_number": None,
            "reservation_timestamp": datetime.date(2023,10,10),
            "check_in_date": datetime.date(2023,10,11),
            "check_out_date": datetime.date(2023,10,12),
            "guests": 1,
            "number_of_extra_beds": None,
            "cost": None,
            "invoice_id": None,
        }
    ]

    rooms = database.session.query(Rooms).options(joinedload(Rooms.bookings), joinedload(Rooms.room_type)).all()
    for customer_info, invoice_info, booking_info in zip(customer_infos, invoice_infos, booking_infos):
        # create new customer
        new_customer = Customers(**customer_info)

        # set values for invoice based on booking
        invoice_info["due_date"] = booking_info["reservation_timestamp"] + datetime.timedelta(days=10)
       
        # create new invoice and flush additions
        new_invoice = Invoices(**invoice_info)
        
        database.session.add_all([new_customer, new_invoice])
        database.session.commit()

        # set values of booking info with new customer and new invoice
        booking_info["customer_id"] = new_customer.id
        booking_info["invoice_id"] = new_invoice.id

        # get a random room based on availability and guests
        rooms = get_available_rooms(database,
                                    booking_info["check_in_date"],
                                    booking_info["check_out_date"])
        rooms = [room for room in rooms if room.room_type.max_capacity >= booking_info["guests"]]
        room = random.choice(rooms)
        booking_info["room_number"] = room.room_number

        # calculate cost
        booking_info["number_of_extra_beds"] = booking_info["guests"] - 2 if booking_info["guests"] > 1 else 0
        nights = (booking_info["check_out_date"] - booking_info["check_in_date"]).days
        cost_extra_bed_per_night = booking_info["number_of_extra_beds"] * 200
        booking_info["cost"] = (nights * (cost_extra_bed_per_night + room.room_type.base_rate_per_night))

        new_booking = Bookings(**booking_info)
        database.session.add(new_booking)
        database.session.commit()

    b_wilson = database.session.query(Customers).filter_by(first_name="Ben").options(joinedload(Customers.bookings)).one()
    b_wilson_booking = b_wilson.bookings[0]
    b_wilson_invoice = b_wilson_booking.invoice
    b_wilson_invoice.payment_timestamp = b_wilson_booking.reservation_timestamp + datetime.timedelta(days=1)
    b_wilson_invoice.payment_amount = b_wilson_booking.cost
    database.session.commit()