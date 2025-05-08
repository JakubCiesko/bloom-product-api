from motor.motor_asyncio import AsyncIOMotorClient
from os import getenv

MONGO_URI = getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)

db = client["bloomreach"]
products_collection = db["products"]
events_collection = db["events"]
products_stats_collection = db["products_stats"]
category_stats_collection = db["category_stats"]