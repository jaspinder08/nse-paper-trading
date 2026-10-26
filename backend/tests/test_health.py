import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    """Test that GET /v1/health returns 200 OK and healthy status."""
    response = await async_client.get("/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["trading_mode"] == "PAPER"
    assert data["database_status"] == "connected"
    assert "timestamp" in data
    assert "environment" in data
    assert "details" in data
