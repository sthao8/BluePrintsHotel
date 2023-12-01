import os

from flask_sqlalchemy import SQLAlchemy

from models import Hotels, RoomTypes, RoomBeds, Images, Rooms, BedTypes, AmenityTypes, RoomAmenities 


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
        base_rate_per_night = 15000,
        room_size = 40
        )
    
    standard_single = RoomTypes(
        name="Standard single",
        description="These simple no-frills rooms are perfect for single travelers on short-stay visits.",
        base_rate_per_night = 900,
        room_size = 15
        )

    standard_double = RoomTypes(
        name="Standard double",
        description="These double rooms offer great quality per price!",
        base_rate_per_night=10000,
        room_size = 25
        )
    database.session.add_all([luxe_double, standard_double, standard_single])
    database.session.commit()

    #TODO: get your images here, and then insert them into the table
    # image_dir_paths = {
    #     standard_single.id: "/static/room_images/standard_single",
    #     standard_double.id: "/static/room_images/standard_double",
    #     luxe_double.id: "/static/room_images/luxe_double"
    # }

    # for id, image_dir_path in image_dir_paths.items():
    #     image_paths = get_images_in_folder(image_dir_path)
    #     for image_path in image_paths:
    #         image = Images(url=image_path, room_type_id=id)
    #         database.session.add(image)

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
        hotel_id=blueprint_hotel.id,
        room_type=luxe_double.id,
        )
    room_102 = Rooms(
        room_number=102,
        hotel_id=blueprint_hotel.id,
        room_type=standard_single.id,
        )
    room_103 = Rooms(
        room_number=103,
        hotel_id=blueprint_hotel.id,
        room_type=standard_double.id,
        )
    room_104 = Rooms(
        room_number=104,
        hotel_id=blueprint_hotel.id,
        room_type=standard_single.id,
        )
    room_105 = Rooms(
        room_number=105,
        hotel_id=blueprint_hotel.id,
        room_type=standard_single.id,
        )
    
    room_201 = Rooms(
        room_number=201,
        hotel_id=blueprint_hotel.id,
        room_type=luxe_double.id,
        )
    room_202 = Rooms(
        room_number=202,
        hotel_id=blueprint_hotel.id,
        room_type=standard_single.id,
        )
    room_203 = Rooms(
        room_number=203,
        hotel_id=blueprint_hotel.id,
        room_type=standard_double.id,
        )
    room_204 = Rooms(
        room_number=204,
        hotel_id=blueprint_hotel.id,
        room_type=standard_single.id,
        )
    room_205 = Rooms(
        room_number=205,
        hotel_id=blueprint_hotel.id,
        room_type=standard_single.id,
        )
    
    rooms = [room_101, room_102, room_103, room_104, room_105, room_201, room_202, room_203, room_204, room_205]
    database.session.add_all(rooms)
    database.session.commit()
