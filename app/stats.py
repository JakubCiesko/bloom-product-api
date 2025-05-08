from datetime import datetime
from app.db import products_collection, events_collection, products_stats_collection


async def calculate_ctr(clicks: int, views: int) -> float:
    return clicks / views if views else 0.0

async def calculate_bounce_rate(clicks:int, views: int) -> float:
    return (views - clicks) / views if views else 0.0

async def calculate_engagement(clicks: int, views: int) -> int: 
    return clicks + views


async def compute_stats() -> list[dict]:
    pipeline = [
        {
            "$group": {
                "_id": "$product_id",
                "views": {
                    "$sum": {"$cond": [{"$eq": ["$action", "view"]}, 1, 0]}
                },
                "clicks": {
                    "$sum": {"$cond": [{"$eq": ["$action", "click"]}, 1, 0]}
                },
                "unique_view_users": {
                    "$addToSet": {
                        "$cond": [{"$eq": ["$action", "view"]}, "$user_id", None]
                    }
                },
                "unique_click_users": {
                    "$addToSet": {
                        "$cond": [{"$eq": ["$action", "click"]}, "$user_id", None]
                    }
                }
            }
        },
        {
            "$project": {
                "views": 1,
                "clicks": 1,
                "unique_view_count": {
                    "$size": {
                        "$setDifference": ["$unique_view_users", [None]]
                    }
                },
                "unique_click_count": {
                    "$size": {
                        "$setDifference": ["$unique_click_users", [None]]
                    }
                }
            }
        }
    ]
    cursor = events_collection.aggregate(pipeline)
    product_stats = []
    async for doc in cursor:
        ctr = await calculate_ctr(doc["clicks"], doc["views"])
        bounce_rate = await calculate_bounce_rate(doc["clicks"], doc["views"])
        engagement = await calculate_engagement(doc["clicks"], doc["views"])
        product_stats.append({
            "product_id": doc["_id"],
            "views": doc["views"],
            "clicks": doc["clicks"],
            "ctr": ctr,
            "bounce_rate": bounce_rate,
            "engagement": engagement,
            "unique_view_count": doc["unique_view_count"],
            "unique_click_count": doc["unique_click_count"],
            "last_updated": datetime.now()
        })
    return product_stats

async def store_stats(stats: list[dict]):
    await products_stats_collection.delete_many({})
    if stats:
        await products_stats_collection.insert_many(stats)

async def compute_and_store_stats():
    stats = await compute_stats()
    await store_stats(stats)
