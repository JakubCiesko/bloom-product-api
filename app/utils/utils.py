from typing import Optional, Any 
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
        query = {}
        if id is not None:
            query["id"] = id
        if title:
            query["title"] = {"$regex": title, "$options": "i"}
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
        collection:AsyncIOMotorCollection, 
        stats_collection: AsyncIOMotorCollection) -> list:
    products_cursor = collection.find(query)
    products = []
    async for product in products_cursor:
        stats = await stats_collection.find_one({"product_id": product["id"]})
        product["stats"] = stats or {}
        product = await sanitize_product_output(product) 
        products.append(product)
    return products 
