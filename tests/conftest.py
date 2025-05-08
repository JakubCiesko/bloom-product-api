import pytest
from ..app.main import app
from httpx import AsyncClient, ASGITransport

# this code fixes issues with event loop and pytests

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        print("Client is ready")
        yield client