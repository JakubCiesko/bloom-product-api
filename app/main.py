import random
import logging 
import asyncio
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, Request, Query
from contextlib import asynccontextmanager
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from .services.updater import Updater
from .services.recommender import (
    CoOccurenceRecommender, 
    UserBasedCollaborativeRecommender
)
from .utils.utils import (
    compose_product_query_parameters,
    get_products_from_collection, 
    get_group_stats_from_collection
)
from .db import (
    products_collection, 
    products_stats_collection,
    category_stats_collection,
    events_collection
)
from .models import (
    ProductModel,
    EventModel
)

logger = logging.getLogger('uvicorn.error')

recommenders = {
    "user_dependent": None, 
    "user_independent": None
}

updater = Updater(
    recommender_refresh_time=300,
    stats_refresh_time=300
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for setting up and tearing down background tasks.
    
    This sets up the two recommenders, initiates the periodic tasks for updating
    the recommenders and stats, and runs background tasks to keep the recommenders
    and stats fresh."""
    # set up regular statistics update 
    global recommenders, updater
    user_independent_recommender = CoOccurenceRecommender(alpha_smoothing=3)
    user_dependent_recommender = UserBasedCollaborativeRecommender()
    await user_independent_recommender._initialize()
    await user_dependent_recommender._initialize()
    recommenders["user_dependent"] = user_dependent_recommender
    recommenders["user_independent"] = user_independent_recommender
    asyncio.create_task(updater.periodic_recommender_update(user_dependent_recommender))
    asyncio.create_task(updater.periodic_recommender_update(user_independent_recommender))
    asyncio.create_task(updater.periodic_stats_update())
    yield
    # anything before shut down

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Root endpoint that renders the index page.

    This endpoint serves the main page of the application and includes the current
    server time. It uses Jinja2 templates for rendering the HTML.

    Args:
        request (Request): The request object, used for rendering the template.

    Returns:
        HTMLResponse: The rendered HTML content with the current time."""
    now = datetime.now()
    return templates.TemplateResponse(
        request=request, name="index.html", context={"now": now}
    )

@app.get("/products", response_class=JSONResponse)
async def get_products(
    id: Optional[int] = None,
    title: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    color: Optional[str] = None,
    material: Optional[str] = None,
    sizes: Optional[list[str]] = Query(None),
    brand: Optional[str] = None,
):
    """Retrieve a list of products based on the given query parameters.

    This endpoint accepts filters for product attributes like id, title, category,
    price range, color, material, sizes, and brand. It returns the products that
    match the provided criteria.

    Args:
        id (Optional[int]): Product ID to filter by.
        title (Optional[str]): Title or part of the title of the product.
        category (Optional[str]): Product category to filter by.
        min_price (Optional[float]): Minimum price for filtering products.
        max_price (Optional[float]): Maximum price for filtering products.
        color (Optional[str]): Color of the product.
        material (Optional[str]): Material of the product.
        sizes (Optional[list[str]]): Sizes of the product.
        brand (Optional[str]): Brand of the product.

    Returns:
        JSONResponse: A JSON response containing the filtered products and group statistics."""
    try: 
        query = await compose_product_query_parameters(
            id, 
            title, 
            category,
            min_price, 
            max_price, 
            color, 
            material,
            sizes,
            brand
        )
        products = await get_products_from_collection(query, products_collection, products_stats_collection)
        group_stats = await get_group_stats_from_collection(query, category_stats_collection)
        if products: 
            response = JSONResponse({"products": products, "group_stats": group_stats})
        else: 
            response = JSONResponse({"products": None, "group_stats": None}, status_code=404) # might drop this, depends on needed behaviour
    except Exception as e: 
        response = JSONResponse({"Error": f"{e}"}, status_code=500)
    return response 


@app.get("/recommend", response_class=JSONResponse)
async def recommend_product(product_id:int=None, user_id:int=None, recommend_n:int=5, sample:bool=False):
    """Get product recommendations based on the given product ID and user ID.

    This endpoint returns the top N recommended products for a user or based on 
    a given product. The recommendations can be generated using either a user-dependent
    or user-independent recommender.

    Args:
        product_id (int): The product ID for which recommendations are needed.
        user_id (int, optional): The user ID to personalize recommendations (if not provided, 
                                  user-independent recommendations are used).
        recommend_n (int): The number of recommendations to return.
        sample (bool): Whether to sample the recommendations randomly.

    Returns:
        JSONResponse: A JSON response containing a list of recommended product IDs."""
    recommender = recommenders["user_dependent"] if user_id else recommenders["user_independent"]
    try: 
        recommended_product_ids = await recommender.recommend(
            product_id=product_id, 
            top_n=recommend_n, 
            sample=sample, 
            user_id=user_id
        )

        if not recommended_product_ids and user_id: # user_dependent recommender failed
            logger.info("User Dependent Recommender Failed. Using Independent Recommender...")
            recommended_product_ids = await recommenders["user_independent"].recommend(
                product_id=product_id or random.choice(range(1, 20)), # if no product_id 
                top_n=recommend_n, 
                sample=sample, 
                user_id=user_id
            )
        query = {"id": {"$in": recommended_product_ids}} 
        products = await get_products_from_collection(query, products_collection, products_stats_collection)
        if products:
            response = JSONResponse(products)
        else:
            response = JSONResponse([], status_code=404)
    except Exception as e:
        logger.error(f"Recommendation failed: {e}")
        response = JSONResponse([{"Error": f"{e}"}], status_code=500)
    return response

@app.post("/products", response_class=JSONResponse)
async def create_product(product: ProductModel):
    """Create a new product and store it in the database.

    This endpoint allows users to create a new product by providing the necessary
    details such as ID, title, category, price, and other attributes. It checks 
    for duplicate products based on the ID before inserting the new product.

    Args:
        product (ProductModel): The product data to be inserted.

    Returns:
        JSONResponse: A success message or error message based on the outcome."""
    try:
        existing = await products_collection.find_one({"id": product.id})
        if existing:
            return JSONResponse({"error": "Product with this ID already exists."}, status_code=400)
        await products_collection.insert_one(product.model_dump())
        return JSONResponse({"message": "product creation success"})
    except Exception as e:
        logger.error(f"Product creation failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/events", response_class=JSONResponse)
async def create_event(event: EventModel):
    """Create a new event and log it in the database.

    This endpoint allows users to log an event related to a product. Events can
    be either a 'view' or 'click'. The event is stored in the database with a
    timestamp.

    Args:
        event (EventModel): The event data to be logged.

    Returns:
        JSONResponse: A success message or error message based on the outcome."""
    try:
        if event.action not in ["view", "click"]:
            return JSONResponse({"error": "Invalid action. Must be 'view' or 'click'."}, status_code=400)
        event_data = event.model_dump()
        event_data["timestamp"] = event.timestamp or datetime.now()
        await events_collection.insert_one(event_data)
        return JSONResponse({"message": "event creation success"})
    except Exception as e:
        logger.error(f"Event logging failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/force_update", response_class=JSONResponse)
async def force_update():
    """Force an update of recommenders and stats.

    This endpoint triggers the manual update of both the user-dependent and user-independent
    recommenders, as well as the statistics. It is useful for refreshing the system's
    recommendations and stats without waiting for the regular update interval.

    Returns:
        JSONResponse: A message indicating the update status."""
    try: 
        logger.info("Forcing update of recommenders and stats.")
        await updater.update_recommender(recommenders["user_dependent"])
        await updater.update_recommender(recommenders["user_independent"])
        await updater.update_stats()
        return JSONResponse({"Status": "done"})
    except Exception as e: 
        logger.error(f"Error occured during forced update: {e}")
        return JSONResponse({"Error": f"{e}"}, status_code=500)
