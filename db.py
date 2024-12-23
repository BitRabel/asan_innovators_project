
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://asaninnovatorsprojectguide:bXsxafE4YWAn0bRb@cluster0.ikhda.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["qr_attendance"]
users_collection = db["users"]
attendance_collection = db["attendance"]
