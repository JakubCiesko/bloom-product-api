import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_post_create_product_success(client: AsyncClient):
    """Test product creation with valid data, ensuring a successful response."""
    new_product = {
        "id": 99999,
        "title": "Test Tee",
        "category": "t-shirts",
        "price": 29.99,
        "color": "Blue",
        "material": "Cotton",
        "sizes": ["S", "M", "L"],
        "brand": "TestBrand"
    }
    response = await client.post("/products", json=new_product)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "message" in data
    assert data["message"] == "product creation success"


@pytest.mark.anyio
async def test_post_create_duplicate_product_fails(client: AsyncClient):
    """Test product creation with a duplicate ID, ensuring it fails with a 400 error."""
    existing_product = {
        "id": 99999,  # Same as above
        "title": "Test Tee Again",
        "category": "t-shirts",
        "price": 29.99,
        "color": "Blue",
        "material": "Cotton",
        "sizes": ["S", "M", "L"],
        "brand": "TestBrand"
    }
    response = await client.post("/products", json=existing_product)
    assert response.status_code == 400, response.text
    data = response.json()
    assert "error" in data
    assert data["error"] == "Product with this ID already exists."

@pytest.mark.anyio
async def test_post_create_event_success(client: AsyncClient):
    """Test event creation with valid data, ensuring a successful response."""
    new_event = {
        "user_id": 123,
        "product_id": 99999,
        "action": "view"
    }
    response = await client.post("/events", json=new_event)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "message" in data
    assert data["message"] == "event creation success"

@pytest.mark.anyio
async def test_post_create_event_invalid_action_fails(client: AsyncClient):
    """Test event creation with an invalid action, ensuring it fails with a 400 error."""
    invalid_event = {
        "user_id": 123,
        "product_id": 99999,
        "action": "purchase" 
    }
    response = await client.post("/events", json=invalid_event)
    assert response.status_code == 400, response.text
    data = response.json()
    assert "error" in data
    assert "Invalid action" in data["error"]
