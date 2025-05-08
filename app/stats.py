import numpy as np
from typing import Any
from datetime import datetime
from app.db import (
    products_collection, 
    events_collection, 
    products_stats_collection,
    category_stats_collection,
    STORED_CATEGORIES
)

async def calculate_ctr(clicks: int, views: int) -> float:
    """Calculate the click-through rate (CTR) based on the number of clicks and views.

    Args:
        clicks (int): The number of clicks.
        views (int): The number of views.

    Returns:
        float: The CTR, which is the ratio of clicks to views. Returns 0.0 if views is 0."""
    return clicks / views if views else 0.0

async def calculate_bounce_rate(clicks:int, views: int) -> float:
    """Calculate the bounce rate based on the number of clicks and views.

    Args:
        clicks (int): The number of clicks.
        views (int): The number of views.

    Returns:
        float: The bounce rate, which is the ratio of non-clicking viewers (views - clicks) to views. 
              Returns 0.0 if views is less than clicks or if views is 0."""
    return (views - clicks) / views if views and views >= clicks else 0.0

async def calculate_engagement(clicks: int, views: int) -> int: 
    """Calculate the engagement score, which is the sum of clicks and views.

    Args:
        clicks (int): The number of clicks.
        views (int): The number of views.

    Returns:
        int: The engagement score, which is the total of clicks and views."""
    return clicks + views

async def compute_stats() -> list[dict[str, Any]]:
    """Compute statistics for each product based on click and view actions in the events collection.
    Returns:
        list[dict]: A list of dictionaries, where each dictionary contains statistics for a product,
                    including views, clicks, CTR, bounce rate, engagement, and unique view and click counts."""
    
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
    """Store the computed product statistics in the database.

    Args:
        stats (list[dict]): A list of dictionaries containing product statistics to be stored."""
    await products_stats_collection.delete_many({})
    if stats:
        await products_stats_collection.insert_many(stats)

async def store_category_stats(category_stats: dict):
    """Store the computed category statistics in the database.

    Args:
        category_stats (dict): A dictionary containing category statistics, where keys are categories and values are their respective stats."""
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

async def compute_category_stats(category_name) -> dict[str, dict[str, Any]]:
    """Compute statistics for a specific category, including views, clicks, unique users, and engagement metrics.

    Args:
        category_name (str): The category name to compute statistics for.

    Returns:
        dict: A dictionary containing computed statistics for the category, including total views, clicks, unique users, and various engagement metrics.
    """
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
    """Compute and store both product-level and category-level statistics. The function computes product-level stats such as CTR, bounce rate, engagement, and unique user counts. It also computes category-level stats like total views, total clicks, unique user counts, and other metrics, and stores all the statistics in the database. This function is called periodically to refresh stats."""
    stats = await compute_stats()
    await store_stats(stats)
    for category in STORED_CATEGORIES:
        category_stats = await compute_category_stats(category)
        await store_category_stats(category_stats)
