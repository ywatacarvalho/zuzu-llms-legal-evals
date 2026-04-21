import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

_FIVE_MODELS = [
    "LiquidAI/LFM2-24B-A2B",
    "openai/gpt-oss-20b",
    "essentialai/rnj-1-instruct",
    "arize-ai/qwen-2-1.5b-instruct",
    "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, email: str) -> str:
    resp = await client.post("/api/v1/auth/register", json={"email": email, "password": "pass"})
    return resp.json()["access_token"]


async def _create_case(client: AsyncClient, token: str) -> str:
    with patch("app.services.case_service.pdfplumber") as mp:
        mp.open.return_value.__enter__.return_value.pages = []
        resp = await client.post(
            "/api/v1/cases",
            files={"file": ("c.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
            data={"title": "T"},
            headers=_auth(token),
        )
    return resp.json()["id"]


async def _create_frozen_rubric(client: AsyncClient, token: str, case_id: str, db_session) -> str:
    """Create a rubric via API, then freeze it directly in the test DB session."""
    with patch(
        "app.api.routes.rubrics._build_rubric_background",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            "/api/v1/rubrics",
            json={
                "case_id": case_id,
                "question": "What is the applicable standard of review?",
            },
            headers=_auth(token),
        )
    rubric_id = resp.json()["id"]

    # Freeze the rubric directly in the test DB session
    from app.repositories.rubric_repository import RubricRepository  # noqa: PLC0415

    repo = RubricRepository(db_session)
    rubric = await repo.get_by_id(uuid.UUID(rubric_id))
    rubric.criteria = [
        {"id": "c1", "name": "Accuracy", "description": "Correctness", "weight": 0.5},
        {"id": "c2", "name": "Reasoning", "description": "Logic", "weight": 0.5},
    ]
    rubric.is_frozen = True
    rubric.status = "frozen"
    await db_session.commit()
    await db_session.refresh(rubric)

    return rubric_id


@pytest.mark.asyncio
async def test_list_models_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/evaluations/models")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_models_returns_list(client: AsyncClient) -> None:
    token = await _register(client, "evalm@example.com")
    resp = await client.get("/api/v1/evaluations/models", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert all("id" in m and "name" in m and "provider" in m for m in data)


@pytest.mark.asyncio
async def test_create_evaluation_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/evaluations", json={})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_evaluation_rubric_not_found(client: AsyncClient) -> None:
    token = await _register(client, "eval1@example.com")
    resp = await client.post(
        "/api/v1/evaluations",
        json={
            "rubric_id": "00000000-0000-0000-0000-000000000000",
            "model_names": _FIVE_MODELS,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_evaluation_rejects_too_few_models(client: AsyncClient, db_session) -> None:
    token = await _register(client, "eval2@example.com")
    case_id = await _create_case(client, token)
    rubric_id = await _create_frozen_rubric(client, token, case_id, db_session)
    resp = await client.post(
        "/api/v1/evaluations",
        json={
            "rubric_id": rubric_id,
            "model_names": ["LiquidAI/LFM2-24B-A2B"],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_evaluation_rejects_too_many_models(client: AsyncClient, db_session) -> None:
    token = await _register(client, "eval2b@example.com")
    case_id = await _create_case(client, token)
    rubric_id = await _create_frozen_rubric(client, token, case_id, db_session)
    resp = await client.post(
        "/api/v1/evaluations",
        json={
            "rubric_id": rubric_id,
            "model_names": [
                "LiquidAI/LFM2-24B-A2B",
                "openai/gpt-oss-20b",
                "essentialai/rnj-1-instruct",
                "arize-ai/qwen-2-1.5b-instruct",
                "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
                "openai/gpt-oss-120b",
            ],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 422


_TWO_MODELS = _FIVE_MODELS[:2]


@pytest.mark.asyncio
async def test_create_evaluation_success_with_two_models(client: AsyncClient, db_session) -> None:
    token = await _register(client, "eval2c@example.com")
    case_id = await _create_case(client, token)
    rubric_id = await _create_frozen_rubric(client, token, case_id, db_session)

    with patch(
        "app.api.routes.evaluations.run_evaluation_pipeline",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            "/api/v1/evaluations",
            json={
                "rubric_id": rubric_id,
                "model_names": _TWO_MODELS,
            },
            headers=_auth(token),
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["model_names"] == _TWO_MODELS


@pytest.mark.asyncio
async def test_create_evaluation_rejects_unknown_model(client: AsyncClient, db_session) -> None:
    token = await _register(client, "eval3@example.com")
    case_id = await _create_case(client, token)
    rubric_id = await _create_frozen_rubric(client, token, case_id, db_session)
    resp = await client.post(
        "/api/v1/evaluations",
        json={
            "rubric_id": rubric_id,
            "model_names": [
                "LiquidAI/LFM2-24B-A2B",
                "openai/gpt-oss-20b",
                "unknown-model",
                "google/gemma-3n-E4B-it",
                "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
            ],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_evaluation_rejects_not_frozen_rubric(client: AsyncClient) -> None:
    token = await _register(client, "eval3b@example.com")
    case_id = await _create_case(client, token)

    # Create a rubric but do NOT freeze it
    with patch(
        "app.api.routes.rubrics._build_rubric_background",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            "/api/v1/rubrics",
            json={
                "case_id": case_id,
                "question": "What is the applicable standard of review?",
            },
            headers=_auth(token),
        )
    building_rubric_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/evaluations",
        json={
            "rubric_id": building_rubric_id,
            "model_names": _FIVE_MODELS,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_evaluation_success(client: AsyncClient, db_session) -> None:
    token = await _register(client, "eval4@example.com")
    case_id = await _create_case(client, token)
    rubric_id = await _create_frozen_rubric(client, token, case_id, db_session)

    with patch(
        "app.api.routes.evaluations.run_evaluation_pipeline",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            "/api/v1/evaluations",
            json={
                "rubric_id": rubric_id,
                "model_names": _FIVE_MODELS,
            },
            headers=_auth(token),
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "running"
    assert data["rubric_id"] == rubric_id
    assert data["model_names"] == _FIVE_MODELS


@pytest.mark.asyncio
async def test_list_evaluations(client: AsyncClient) -> None:
    token = await _register(client, "eval5@example.com")
    resp = await client.get("/api/v1/evaluations", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_evaluation_not_found(client: AsyncClient) -> None:
    token = await _register(client, "eval6@example.com")
    resp = await client.get(
        "/api/v1/evaluations/00000000-0000-0000-0000-000000000000",
        headers=_auth(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_evaluation_logs_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/evaluations/00000000-0000-0000-0000-000000000001/logs")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_evaluation_logs_returns_empty_for_new_evaluation(
    client: AsyncClient,
) -> None:
    token = await _register(client, "eval7@example.com")
    resp = await client.get(
        "/api/v1/evaluations/00000000-0000-0000-0000-000000000002/logs",
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "lines" in data
    assert "total" in data
    assert isinstance(data["lines"], list)
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_evaluation_passes_variation_question_when_dual_rubric_mode(
    client: AsyncClient, db_session
) -> None:
    """When dual_rubric_mode=True, run_evaluation_pipeline receives variation_question."""
    token = await _register(client, "evaldual@example.com")
    case_id = await _create_case(client, token)
    rubric_id = await _create_frozen_rubric(client, token, case_id, db_session)

    from app.repositories.rubric_repository import RubricRepository  # noqa: PLC0415

    repo = RubricRepository(db_session)
    rubric = await repo.get_by_id(uuid.UUID(rubric_id))
    rubric.dual_rubric_mode = True
    rubric.variation_question = "Does the variation exception apply?"
    await db_session.commit()

    mock_pipeline = AsyncMock()
    with patch("app.api.routes.evaluations.run_evaluation_pipeline", mock_pipeline):
        resp = await client.post(
            "/api/v1/evaluations",
            json={"rubric_id": rubric_id, "model_names": _TWO_MODELS},
            headers=_auth(token),
        )

    assert resp.status_code == 201
    mock_pipeline.assert_called_once()
    assert (
        mock_pipeline.call_args.kwargs.get("variation_question")
        == "Does the variation exception apply?"
    )


@pytest.mark.asyncio
async def test_create_evaluation_variation_question_is_none_when_not_dual_rubric(
    client: AsyncClient, db_session
) -> None:
    """When dual_rubric_mode is False, variation_question passed to pipeline is None."""
    token = await _register(client, "evalnodual@example.com")
    case_id = await _create_case(client, token)
    rubric_id = await _create_frozen_rubric(client, token, case_id, db_session)

    mock_pipeline = AsyncMock()
    with patch("app.api.routes.evaluations.run_evaluation_pipeline", mock_pipeline):
        resp = await client.post(
            "/api/v1/evaluations",
            json={"rubric_id": rubric_id, "model_names": _TWO_MODELS},
            headers=_auth(token),
        )

    assert resp.status_code == 201
    mock_pipeline.assert_called_once()
    assert mock_pipeline.call_args.kwargs.get("variation_question") is None


@pytest.mark.asyncio
async def test_get_evaluation_logs_returns_lines_with_offset(
    client: AsyncClient,
) -> None:
    from app.services import log_stream

    eid = "00000000-0000-0000-0000-000000000003"
    log_stream.log(eid, "line 1")
    log_stream.log(eid, "line 2")
    log_stream.log(eid, "line 3")

    token = await _register(client, "eval8@example.com")
    resp = await client.get(
        f"/api/v1/evaluations/{eid}/logs?offset=1",
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["lines"]) == 2
