import pytest
from httpx import ASGITransport, AsyncClient
from ..app.main import app


@pytest.mark.anyio
async def test_index(client: AsyncClient):
    """ Test the index route ("/") to ensure it returns a 200 status code,
    content-type is HTML, and the response contains an HTML tag."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html" in response.text.lower()