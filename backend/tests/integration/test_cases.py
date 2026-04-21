import io
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


async def _get_auth_token(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "caseuser@example.com", "password": "pass123"},
    )
    if resp.status_code == 409:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "caseuser@example.com", "password": "pass123"},
        )
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _minimal_pdf_bytes() -> bytes:
    """Minimal valid PDF bytes with one page containing 'Hello World'."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n0\n%%EOF"
    )


@pytest.mark.asyncio
async def test_upload_case_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/api/v1/cases")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_upload_case_rejects_non_pdf(client: AsyncClient) -> None:
    token = await _get_auth_token(client)
    response = await client.post(
        "/api/v1/cases",
        files={"file": ("doc.txt", io.BytesIO(b"plain text"), "text/plain")},
        headers=_auth(token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_case_success(client: AsyncClient) -> None:
    token = await _get_auth_token(client)

    with patch("app.services.case_service.pdfplumber") as mock_plumber:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Sample legal text."
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]
        mock_plumber.open.return_value = mock_pdf

        response = await client.post(
            "/api/v1/cases",
            files={"file": ("case.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            headers=_auth(token),
        )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "case.pdf"
    assert "id" in data


@pytest.mark.asyncio
async def test_upload_case_uses_custom_title(client: AsyncClient) -> None:
    token = await _get_auth_token(client)

    with patch("app.services.case_service.pdfplumber") as mock_plumber:
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = []
        mock_plumber.open.return_value = mock_pdf

        response = await client.post(
            "/api/v1/cases",
            files={"file": ("brief.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "My Custom Title"},
            headers=_auth(token),
        )

    assert response.status_code == 201
    assert response.json()["title"] == "My Custom Title"


@pytest.mark.asyncio
async def test_list_cases_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/cases")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_cases_returns_list(client: AsyncClient) -> None:
    token = await _get_auth_token(client)
    response = await client.get("/api/v1/cases", headers=_auth(token))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_case_not_found(client: AsyncClient) -> None:
    token = await _get_auth_token(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/cases/{fake_id}", headers=_auth(token))
    assert response.status_code == 404
