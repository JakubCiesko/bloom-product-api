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
    get_products_from_collection
)
from .db import (
    products_collection, 
    products_stats_collection
)

logger = logging.getLogger('uvicorn.error')

recommenders = {
    "user_dependent": None, 
    "user_independent": None
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # set up regular statistics update 
    global recommenders
    user_independent_recommender = CoOccurenceRecommender(alpha_smoothing=3)
    user_dependent_recommender = UserBasedCollaborativeRecommender()
    await user_independent_recommender._initialize()
    await user_dependent_recommender._initialize()
    recommenders["user_dependent"] = user_dependent_recommender
    recommenders["user_independent"] = user_independent_recommender
    updater = Updater(
        recommender_refresh_time=300,
        stats_refresh_time=300
    )
    asyncio.create_task(updater.periodic_recommender_updater(user_dependent_recommender))
    asyncio.create_task(updater.periodic_recommender_updater(user_independent_recommender))
    asyncio.create_task(updater.periodic_stats_updater())
    yield
    # anything before shut down

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
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
        if products: 
            response = JSONResponse(products)
        else: 
            response = JSONResponse([], status_code=404) # might drop this, depends on needed behaviour
    except Exception as e: 
        response = JSONResponse([{"Error": f"{e}"}], status_code=500)
    return response 


@app.get("/recommend", response_class=JSONResponse)
async def recommend_product(product_id:int=None, user_id:int=None, recommend_n:int=5, sample:bool=False):
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
                product_id=product_id, 
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