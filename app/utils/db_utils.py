import json 
import logging
import asyncio 
import argparse
import pymongo.errors
from app.stats import compute_and_store_stats
from motor.motor_asyncio import AsyncIOMotorCollection
from app.db import products_collection, events_collection, products_stats_collection

logger = logging.getLogger(__name__)

async def load_json_to_collection(json_file: str, collection:AsyncIOMotorCollection, collection_name:str="", empty_db:bool=True) -> None:
    try: 
        with open(json_file, "r", encoding="UTF-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                if empty_db: 
                    logger.warning(f"Collection {collection_name} cleared due to keep_db_content flag!")
                    await collection.delete_many({})
                result = await collection.insert_many(data)
                logger.info(f"Inserted {len(result.inserted_ids)} documents into '{collection_name}'")
            else: 
                if empty_db: 
                    logger.warning(f"Collection {collection_name} cleared due to keep_db_content flag!")
                    await collection.delete_one({})
                result = await collection.insert_one(data)
                logger.info(f"Inserted 1 document into '{collection_name}'")
    except Exception as e: 
        logger.error(f"Failed to populate collection with {json_file}: {e}") 

async def init_indexes(collection_name: str) -> None:
    try:
        match collection_name: 
            case "products":
                # Products indices for faster query
                logger.info("Creating indices for 'products' collection (id, category, color, category&color)")
                await products_collection.create_index("category")
                await products_collection.create_index("color")
                await products_collection.create_index([("category", 1), ("color", 1)])
                await products_collection.create_index("id", unique=True)
            case "events":
                # Event indices for faster query
                logger.info("Creating indices for 'events' collection (product_id, user_id)") 
                await events_collection.create_index("product_id")
                await events_collection.create_index("user_id")
                logger.info("Indices created.")
                logger.info("DB fully initialized.")
            case _:
                logger.warning("Wrong collection_name") 
    except pymongo.errors.OperationFailure as e:
        logger.error(f"Index creation failed {e}")


async def main(args):
    if args.products:
        logger.info(f"Loading products from {args.products}")
        await load_json_to_collection(args.products, products_collection, "products", args.keep_db_content)
        await init_indexes("products")
    if args.events:
        logger.info(f"Loading events from {args.events}")
        await load_json_to_collection(args.events, events_collection, "events", args.keep_db_content)
        await init_indexes("events")
        #await init_stats()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed MongoDB with product and event data.")
    parser.add_argument('--products', help='Path to products JSON file')
    parser.add_argument('--events', help='Path to events JSON file')
    parser.add_argument('--keep_db_content', action="store_false")
    args = parser.parse_args()
    asyncio.run(main(args))
