from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


class ProductModel(BaseModel):
    """Represents a product model with various attributes such as ID, title, category,
    price, color, material, sizes, and brand.

    Attributes:
        id (int): The unique identifier for the product.
        title (str): The title or name of the product.
        category (str): The category the product belongs to.
        price (float): The price of the product.
        color (str): The color of the product.
        material (str): The material the product is made of.
        sizes (List[str]): A list of available sizes for the product.
        brand (str): The brand of the product."""
    id: int
    title: str
    category: str
    price: float
    color: str
    material: str
    sizes: List[str]
    brand: str

class EventModel(BaseModel):
    """Represents an event related to a user interacting with a product. The event
    includes the user ID, product ID, the action (view or click), and an optional
    timestamp.

    Attributes:
        user_id (int): The unique identifier of the user performing the action.
        product_id (int): The unique identifier of the product being interacted with.
        action (str): The type of action performed by the user, either 'view' or 'click'.
        timestamp (Optional[datetime]): The timestamp of the event. If not provided,
                                          it defaults to the current time."""
    user_id: int
    product_id: int
    action: str  # "view" or "click"
    timestamp: Optional[datetime] = None