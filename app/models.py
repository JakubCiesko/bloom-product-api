from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


class ProductModel(BaseModel):
    id: int
    title: str
    category: str
    price: float
    color: str
    material: str
    sizes: List[str]
    brand: str

class EventModel(BaseModel):
    user_id: int
    product_id: int
    action: str  # "view" or "click"
    timestamp: Optional[datetime] = None