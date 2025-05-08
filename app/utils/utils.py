from typing import Optional, Any 
from ..db import STORED_CATEGORIES
from motor.motor_asyncio import AsyncIOMotorCollection


async def compose_product_query_parameters(
    id: Optional[int] = None,
    title: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    color: Optional[str] = None,
    material: Optional[str] = None,
    sizes: Optional[list[str]] = None,
    brand: Optional[str] = None
    ) -> dict[str, Any]:
        """Constructs a MongoDB query dictionary based on optional product search parameters.

    Args:
        id (Optional[int]): Product ID.
        title (Optional[str]): Product title to search (supports partial match).
        category (Optional[str]): Product category.
        min_price (Optional[float]): Minimum price.
        max_price (Optional[float]): Maximum price.
        color (Optional[str]): Product color.
        material (Optional[str]): Product material.
        sizes (Optional[list[str]]): List of required sizes.
        brand (Optional[str]): Product brand.

    Returns:
        dict[str, Any]: A MongoDB-compatible query dictionary."""
        query = {}
        if id is not None:
            query["id"] = id
        if title:
            query["title"] = {"$regex": {title}, "$options": "i"}
        if category:
            query["category"] = category
        if color:
            query["color"] = color
        if material:
            query["material"] = material
        if brand:
            query["brand"] = brand
        if sizes:
            query["sizes"] = {"$all": sizes}
        if min_price is not None or max_price is not None:
            query["price"] = {}
            if min_price is not None:
                query["price"]["$gte"] = min_price
            if max_price is not None:
                query["price"]["$lte"] = max_price
        return query

async def sanitize_product_output(product: dict[str, Any]) -> dict[str, Any]:
    """Cleans and formats a product dictionary for safe API output.

    Removes internal MongoDB `_id` fields and formats datetime fields.

    Args:
        product (dict[str, Any]): Product document from MongoDB.

    Returns:
        dict[str, Any]: Sanitized product dictionary.""" 
    if product: 
        product.pop("_id")
        stats = product.get("stats", {})    
        if stats: 
            stats.pop("_id")
            stats["last_updated"] = stats["last_updated"].isoformat() 
        product["stats"] = stats
    return product      

async def get_products_from_collection(
        query:dict[str, Any], 
        collection: AsyncIOMotorCollection, 
        stats_collection: AsyncIOMotorCollection) -> list[dict[str,Any]]:
    """Retrieves products matching the given query and enriches them with stats.

    Args:
        query (dict[str, Any]): MongoDB query.
        collection (AsyncIOMotorCollection): Collection to query products from.
        stats_collection (AsyncIOMotorCollection): Collection containing product stats.

    Returns:
        list[dict[str,Any]]: A list of sanitized product documents with attached stats."""

    products_cursor = collection.find(query)
    products = []
    async for product in products_cursor:
        stats = await stats_collection.find_one({"product_id": product["id"]})
        product["stats"] = stats or {}
        product = await sanitize_product_output(product) 
        products.append(product)
    return products 

async def get_group_stats_from_collection(query: dict[str, Any], group_stats_collection: AsyncIOMotorCollection) -> dict[str,list]:
    """Retrieves grouped statistical data for given categories from the stats collection.

    Args:
        query (dict[str, Any]): Dictionary of product category values to filter group stats.
        group_stats_collection (AsyncIOMotorCollection): Collection to query grouped stats.

    Returns:
        dict: Dictionary with category names as keys and lists of grouped stats as values."""
    group_stats = {}
    for category in STORED_CATEGORIES:
        category_value = query.get(category, None)
        if category_value: 
            group_stats_cursor = group_stats_collection.find({"category": category_value})
            group_stats[category] = [
                {k: v for k, v in group_stat.items() if k != "_id"}
                async for group_stat in group_stats_cursor
            ]
    return group_stats
