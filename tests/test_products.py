import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_get_all_products(client: AsyncClient):
    response = await client.get("/products")
    assert response.status_code == 200, response.text
    data = response.json()
    data = data["products"]
    assert isinstance(data, list)
    assert len(data) > 0
    assert isinstance(data[0]["id"], int)

@pytest.mark.anyio
async def test_get_products_by_category(client: AsyncClient): 
    response = await client.get("/products", params={"category": "t-shirts"})
    assert response.status_code == 200, response.text
    data = response.json()
    data = data["products"]
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(product["category"] == "t-shirts" for product in data)

@pytest.mark.anyio
async def test_get_products_nonexisting_category(client: AsyncClient):
    response = await client.get("/products", params={"category": "cars"})
    assert response.status_code == 404, response.text
    data = response.json()
    assert data["products"] is None
    assert data["group_stats"] is None
    

@pytest.mark.anyio
async def test_get_products_by_price_range(client: AsyncClient):
    response = await client.get("/products", params={"min_price": 10.0, "max_price": 100.0})
    assert response.status_code == 200, response.text
    data = response.json()
    data = data["products"]
    assert isinstance(data, list)
    assert all(10.0 <= product["price"] <= 100.0 for product in data)


@pytest.mark.anyio
async def test_get_products_by_sizes(client: AsyncClient):
    response = await client.get("/products", params={"sizes": ["M", "L", "XL"]})
    assert response.status_code == 200, response.text
    data = response.json()
    data = data["products"]
    assert isinstance(data, list)
    assert all(set(["M", "L", "XL"]).intersection(set(product["sizes"])) == {"M", "L", "XL"} for product in data)


@pytest.mark.anyio
async def test_get_products_with_multiple_filters(client: AsyncClient):
    response = await client.get("/products", params={"category": "gloves", "min_price": 10.0, "max_price": 100.0})
    assert response.status_code == 200, response.text
    data = response.json()
    data = data["products"]
    assert isinstance(data, list)
    assert all(
        product["category"] == "gloves" and
        10.0 <= product["price"] <= 100.0
        for product in data
    )

@pytest.mark.anyio
async def test_product_stats(client: AsyncClient):
    response = await client.get("/products", params={"category": "gloves", "min_price": 10.0, "max_price": 100.0})
    assert response.status_code == 200, response.text
    data = response.json()
    assert all(key in data for key in ["products", "group_stats"])
    products = data["products"]
    group_stats = data["group_stats"]
    assert isinstance(products, list)
    assert isinstance(group_stats, dict)
    assert all(
        product["category"] == "gloves" and
        10.0 <= product["price"] <= 100.0
        for product in products
    )
    assert isinstance(products[0]["stats"], dict)
    assert len(products[0]["stats"]) > 0 
    assert all(x in products[0]["stats"] for x in ["product_id", "views", "ctr", "last_updated"])

