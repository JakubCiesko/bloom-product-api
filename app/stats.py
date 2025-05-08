import numpy as np
from datetime import datetime
from app.db import (
    products_collection, 
    events_collection, 
    products_stats_collection,
    category_stats_collection,
    STORED_CATEGORIES
)

async def calculate_ctr(clicks: int, views: int) -> float:
    return clicks / views if views else 0.0

async def calculate_bounce_rate(clicks:int, views: int) -> float:
    return (views - clicks) / views if views and views >= clicks else 0.0

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

async def store_category_stats(category_stats: dict):
    for category, stats in category_stats.items():
        existing_stats = await category_stats_collection.find_one({"category": category})
        
        if existing_stats:
            await category_stats_collection.update_one(
                {"category": category},
                {"$set": stats}
            )
        else:
            await category_stats_collection.insert_one({
                "category": category,
                **stats
            })

async def compute_category_stats(category_name) -> dict:
    pipeline = [
        {
            "$lookup": {
                "from": "products_stats",
                "localField": "id",
                "foreignField": "product_id",
                "as": "stats"
            }
        },
        {
            "$unwind": "$stats"
        },
        {
            "$group": {
                "_id": f"${category_name}",
                "total_views": {"$sum": "$stats.views"},
                "total_clicks": {"$sum": "$stats.clicks"},
                "unique_view_count": {"$sum": "$stats.unique_view_count"},
                "unique_click_count": {"$sum": "$stats.unique_click_count"},
                "product_count": {"$sum": 1},
                "ctr_values": {"$push": "$stats.ctr"},
                "bounce_rate_values": {"$push": "$stats.bounce_rate"},
                "engagement_values": {"$push": "$stats.engagement"}
            }
        }
    ]

    cursor = products_collection.aggregate(pipeline)

    category_stats = {}
    statistic_functions = {
        "mean": np.mean,
        "std": np.std,
        "q25": lambda x: np.quantile(x, 0.25),
        "q75": lambda x: np.quantile(x, 0.75)
    }

    async for doc in cursor:
        category = doc["_id"]
        category_stats[category] = {
            "total_views": doc["total_views"],
            "total_clicks": doc["total_clicks"],
            "unique_view_count": doc["unique_view_count"],
            "unique_click_count": doc["unique_click_count"],
            "product_count": doc["product_count"],
            "ctr_values": doc["ctr_values"],
            "bounce_rate_values": doc["bounce_rate_values"],
            "engagement_values": doc["engagement_values"],
        }

        for feature in ["ctr_values", "bounce_rate_values", "engagement_values"]:
            values = doc[feature]
            for statistic, statistic_fn in statistic_functions.items():
                category_stats[category][f"{statistic}_{feature.replace('_values', '')}"] = statistic_fn(values)

    return category_stats

async def compute_and_store_stats():
    stats = await compute_stats()
    await store_stats(stats)
    for category in STORED_CATEGORIES:
        category_stats = await compute_category_stats(category)
        await store_category_stats(category_stats)
