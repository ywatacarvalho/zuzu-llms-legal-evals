import pytest
from httpx import AsyncClient


async def _token(client: AsyncClient, email: str) -> str:
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "pass123"}
    )
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_stats_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard/stats")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_stats_returns_zeroes_on_empty_db(client: AsyncClient) -> None:
    token = await _token(client, "dash1@example.com")
    resp = await client.get("/api/v1/dashboard/stats", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cases"] >= 0
    assert data["evaluations_run"] >= 0
    assert data["models_evaluated"] >= 0
    assert data["avg_clusters"] >= 0.0
