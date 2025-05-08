from app.db import products_collection, events_collection, products_stats_collection
from datetime import datetime
import asyncio

async def calculate_ctr(clicks: int, views: int) -> float:
    return clicks / views if views else 0.0

async def compute_stats() -> list[dict]:
    pipeline = [
        {"$group": {
            "_id": "$product_id",
            "views": {"$sum": {"$cond": [{"$eq": ["$action", "view"]}, 1, 0]}},
            "clicks": {"$sum": {"$cond": [{"$eq": ["$action", "click"]}, 1, 0]}}
        }}
    ]
    cursor = events_collection.aggregate(pipeline)
    product_stats = []
    async for doc in cursor:
        ctr = await calculate_ctr(doc["clicks"], doc["views"])
        product_stats.append({
            "product_id": doc["_id"],
            "views": doc["views"],
            "clicks": doc["clicks"],
            "ctr": ctr,
            "last_updated": datetime.now()
        })
    return product_stats

async def store_stats(stats: list[dict]):
    await products_stats_collection.delete_many({})
    if stats:
        await products_stats_collection.insert_many(stats)

async def compute_and_store_stats():
    stats = await compute_stats()
    await asyncio.sleep(20)
    await store_stats(stats)
