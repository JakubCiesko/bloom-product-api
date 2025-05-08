from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ProductStatsModel(BaseModel):
    product_id: int
    views: int
    clicks: int
    ctr: float
    last_updated: datetime

class ProductModel(BaseModel):
    id: int
    title: str
    category: str
    price: float
    color: str
    material: str
    sizes: List[str]
    brand: str
    stats: Optional[ProductStatsModel] = None

    class Config:
        orm_mode = True
