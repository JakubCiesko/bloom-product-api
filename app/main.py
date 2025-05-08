import logging 
import asyncio
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, Request, Query
from contextlib import asynccontextmanager
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from .services.stats_update import periodic_stats_updater
from .utils.utils import (
    compose_product_query_parameters,
    sanitize_product_output
)
from .db import (
    products_collection, 
    events_collection, 
    products_stats_collection
)


logger = logging.getLogger('uvicorn.error')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # set up regular statistics update 
    asyncio.create_task(periodic_stats_updater())
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
        products_cursor = products_collection.find(query)
        products = []
        async for product in products_cursor:
            stats = await products_stats_collection.find_one({"product_id": product["id"]})
            product["stats"] = stats or {}
            product = await sanitize_product_output(product) 
            products.append(product)
        if products: 
            response = JSONResponse(products)
        else: 
            response = JSONResponse([], status_code=404) # might drop this, depends on needed behaviour
    except Exception as e: 
        response = JSONResponse([{"Error": f"{e}"}], status_code=500)
    return response 


