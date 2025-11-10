from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["pg_db"]
rooms_collection = db["rooms"]

rooms_collection.delete_many({})

rooms = [
    {"room_id": 1, "name": "Deluxe Room", "price": 5000, "type": "Single", "rating": 4.5, "available": 1, "image": "1.jpeg"},
    {"room_id": 2, "name": "Luxury Suite", "price": 8000, "type": "Double", "rating": 4.8, "available": 1, "image": "2.jpeg"},
    {"room_id": 3, "name": "Standard Room", "price": 3000, "type": "Single", "rating": 4.2, "available": 1, "image": "3.jpeg"},
    {"room_id": 4, "name": "Family Suite", "price": 10000, "type": "Triple", "rating": 4.7, "available": 1, "image": "4.jpeg"},
    {"room_id": 5, "name": "Economy Room", "price": 2000, "type": "Single", "rating": 3.9, "available": 1, "image": "5.jpeg"},
    {"room_id": 6, "name": "Sea View Room", "price": 7000, "type": "Double", "rating": 4.6, "available": 1, "image": "6.jpeg"},
    {"room_id": 7, "name": "Garden View Room", "price": 6000, "type": "Double", "rating": 4.4, "available": 1, "image": "7.jpeg"},
    {"room_id": 8, "name": "Penthouse Suite", "price": 15000, "type": "Luxury", "rating": 5.0, "available": 1, "image": "8.jpeg"}
]

rooms_collection.insert_many(rooms)
print("Rooms inserted with images")
