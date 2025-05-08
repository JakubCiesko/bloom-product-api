import pytest
from httpx import AsyncClient
from ..app.main import recommenders, CoOccurenceRecommender, UserBasedCollaborativeRecommender

@pytest.fixture(scope="module", autouse=True)
async def initialize_recommenders():
    """Fixture to initialize recommenders before tests, ensuring they are ready for use."""
    user_independent = CoOccurenceRecommender()
    await user_independent._initialize()

    user_dependent = UserBasedCollaborativeRecommender()
    await user_dependent._initialize()

    recommenders["user_independent"] = user_independent
    recommenders["user_dependent"] = user_dependent


@pytest.mark.anyio
async def test_recommend_by_product_id(client: AsyncClient):
    """Test recommending products based on a given product ID."""
    response = await client.get("/recommend", params={"product_id": 1})
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]

@pytest.mark.anyio
async def test_recommend_by_user_id(client: AsyncClient):
    """Test recommending products based on a given user ID."""
    response = await client.get("/recommend", params={"user_id": 11})
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]

@pytest.mark.anyio
async def test_recommend_by_user_and_product(client: AsyncClient):
    """Test recommending products based on both a given user ID and product ID."""
    response = await client.get("/recommend", params={"user_id": 11, "product_id": 1})
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]

@pytest.mark.anyio
async def test_recommend_with_sample_flag(client: AsyncClient):
    """Test recommending products with the sample flag set to true."""
    response = await client.get("/recommend", params={"product_id": 1, "sample": True})
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

@pytest.mark.anyio
async def test_recommend_invalid_product(client: AsyncClient):
    """Test recommending products with an invalid product ID, expecting potential errors."""
    response = await client.get("/recommend", params={"product_id": 999999})
    assert response.status_code in [200, 404, 500], response.text

@pytest.mark.anyio
async def test_recommend_invalid_user(client: AsyncClient):
    """Test recommending products with an invalid product ID, expecting potential errors."""
    response = await client.get("/recommend", params={"user_id": 999999})
    assert response.status_code in [200, 404, 500], response.text

@pytest.mark.anyio
async def test_recommend_missing_params(client: AsyncClient):
    """Test recommending products with missing parameters, expecting an error response."""
    response = await client.get("/recommend")
    assert response.status_code == 500, response.text
    data = response.json()
    assert isinstance(data, list)
    assert "Error" in data[0]