"""Integration tests for the Analysis module (steps 5–8)."""

import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.routes.analysis import _failed, _running


@pytest.fixture(autouse=True)
def _clear_analysis_state():
    """Clear in-memory analysis tracking sets between tests."""
    _running.clear()
    _failed.clear()
    yield
    _running.clear()
    _failed.clear()


_FIVE_MODELS = [
    "LiquidAI/LFM2-24B-A2B",
    "openai/gpt-oss-20b",
    "essentialai/rnj-1-instruct",
    "arize-ai/qwen-2-1.5b-instruct",
    "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
]

_MOCK_CRITERIA = [
    {"id": "accuracy", "name": "Accuracy", "description": "Factual correctness.", "weight": 0.5},
    {
        "id": "reasoning",
        "name": "Reasoning",
        "description": "Quality of legal reasoning.",
        "weight": 0.5,
    },
]

_MOCK_ANALYSIS_RESULT = {
    "k": 3,
    "clusters": [
        {
            "cluster_id": 0,
            "response_indices": list(range(70)),
            "centroid_index": 5,
            "centroid_response_text": "The standard of review is de novo.",
        },
        {
            "cluster_id": 1,
            "response_indices": list(range(70, 130)),
            "centroid_index": 72,
            "centroid_response_text": "Under the abuse of discretion standard...",
        },
        {
            "cluster_id": 2,
            "response_indices": list(range(130, 200)),
            "centroid_index": 145,
            "centroid_response_text": "The court applies a clearly erroneous standard.",
        },
    ],
    "centroid_indices": [5, 72, 145],
    "scores": {"0": 0.85, "1": 0.72, "2": 0.61},
    "winning_cluster": 0,
    "model_shares": {
        "LiquidAI/LFM2-24B-A2B": 0.32,
        "openai/gpt-oss-20b": 0.24,
        "google/gemma-3n-E4B-it": 0.20,
        "arize-ai/qwen-2-1.5b-instruct": 0.14,
        "meta-llama/Meta-Llama-3-8B-Instruct-Lite": 0.10,
    },
    "weighting_mode": "heuristic",
    "baseline_scores": {"0": {"accuracy": 0.9, "reasoning": 0.8}, "1": {}, "2": {}},
    "weighting_comparison": {},
}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, email: str) -> str:
    resp = await client.post("/api/v1/auth/register", json={"email": email, "password": "pass123"})
    return resp.json()["access_token"]


async def _create_case_with_text(client: AsyncClient, token: str) -> str:
    """Create a case that has raw_text (non-empty PDF mock)."""
    with patch("app.services.case_service.pdfplumber") as mp:
        mock_page = mp.open.return_value.__enter__.return_value
        mock_page.pages = [
            type("P", (), {"extract_text": lambda self: "Legal case text for testing."})()
        ]
        resp = await client.post(
            "/api/v1/cases",
            files={"file": ("case.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Test Case"},
            headers=_auth(token),
        )
    return resp.json()["id"]


async def _create_done_evaluation(client: AsyncClient, token: str, case_id: str, db_session) -> str:
    """Create an evaluation via a frozen rubric and patch its status to 'done'."""
    from app.repositories.rubric_repository import RubricRepository  # noqa: PLC0415

    # First create and freeze a rubric
    with patch(
        "app.api.routes.rubrics._build_rubric_background",
        new_callable=AsyncMock,
    ):
        rubric_resp = await client.post(
            "/api/v1/rubrics",
            json={
                "case_id": case_id,
                "question": "What is the applicable standard of review?",
            },
            headers=_auth(token),
        )
    rubric_id = rubric_resp.json()["id"]

    # Freeze the rubric using the test DB session
    repo = RubricRepository(db_session)
    rubric = await repo.get_by_id(uuid.UUID(rubric_id))
    rubric.criteria = _MOCK_CRITERIA
    rubric.is_frozen = True
    rubric.status = "frozen"
    await db_session.commit()
    await db_session.refresh(rubric)

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
    return resp.json()["id"]


# ── Auth guards ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_analysis_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(f"/api/v1/analysis/{uuid.uuid4()}/run")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_analysis_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/analysis/{uuid.uuid4()}")
    assert resp.status_code in (401, 403)


# ── 404 / 422 guards ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_analysis_evaluation_not_found(client: AsyncClient) -> None:
    token = await _register(client, "analysis1@example.com")
    resp = await client.post(f"/api/v1/analysis/{uuid.uuid4()}/run", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_analysis_not_found(client: AsyncClient) -> None:
    token = await _register(client, "analysis2@example.com")
    resp = await client.get(f"/api/v1/analysis/{uuid.uuid4()}", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_analysis_evaluation_not_done(client: AsyncClient, db_session) -> None:
    """Running analysis on a non-done evaluation must return 422."""
    from app.repositories.rubric_repository import RubricRepository  # noqa: PLC0415

    token = await _register(client, "analysis3@example.com")
    case_id = await _create_case_with_text(client, token)

    # Create and freeze a rubric
    with patch(
        "app.api.routes.rubrics._build_rubric_background",
        new_callable=AsyncMock,
    ):
        rubric_resp = await client.post(
            "/api/v1/rubrics",
            json={
                "case_id": case_id,
                "question": "What is the standard of review?",
            },
            headers=_auth(token),
        )
    rubric_id = rubric_resp.json()["id"]

    repo = RubricRepository(db_session)
    rubric = await repo.get_by_id(uuid.UUID(rubric_id))
    rubric.criteria = _MOCK_CRITERIA
    rubric.is_frozen = True
    rubric.status = "frozen"
    await db_session.commit()
    await db_session.refresh(rubric)

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
    eval_id = resp.json()["id"]

    # Evaluation status is 'running', not 'done' -- analysis must be rejected
    resp = await client.post(f"/api/v1/analysis/{eval_id}/run", headers=_auth(token))
    assert resp.status_code == 422


# ── Success path ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_analysis_returns_202(client: AsyncClient) -> None:
    """POST /run returns 202 and queues a background task."""
    token = await _register(client, "analysis4@example.com")
    eval_id_str = str(uuid.uuid4())
    eval_uuid = uuid.UUID(eval_id_str)

    from app.models.evaluation import StatusEnum  # noqa: PLC0415

    fake_evaluation = type(
        "Evaluation",
        (),
        {
            "id": eval_uuid,
            "status": StatusEnum.done,
            "case_id": uuid.uuid4(),
            "rubric_id": uuid.uuid4(),
            "question": "What is the standard of review?",
        },
    )()
    fake_rubric = type("Rubric", (), {"criteria": _MOCK_CRITERIA})()

    _fake_responses = [
        type("MR", (), {"response_text": "text", "model_name": m, "run_index": i})()
        for i, m in enumerate(_FIVE_MODELS * 40)
    ]

    with (
        patch(
            "app.api.routes.analysis.AnalysisRepository.get_by_evaluation_id",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.api.routes.analysis.EvaluationRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=fake_evaluation,
        ),
        patch(
            "app.api.routes.analysis.RubricRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=fake_rubric,
        ),
        patch(
            "app.api.routes.analysis._load_responses",
            new_callable=AsyncMock,
            return_value=_fake_responses,
        ),
        patch(
            "app.api.routes.analysis._run_analysis_background",
            new_callable=AsyncMock,
        ) as mock_bg,
    ):
        resp = await client.post(f"/api/v1/analysis/{eval_id_str}/run", headers=_auth(token))

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "running"
    mock_bg.assert_called_once()


@pytest.mark.asyncio
async def test_run_analysis_returns_existing(client: AsyncClient) -> None:
    """POST /run returns existing analysis with 200 (idempotent)."""
    token = await _register(client, "analysis5@example.com")
    eval_id_str = str(uuid.uuid4())
    eval_uuid = uuid.UUID(eval_id_str)

    _fake_stored = type(
        "Analysis",
        (),
        {
            "id": uuid.uuid4(),
            "evaluation_id": eval_uuid,
            **_MOCK_ANALYSIS_RESULT,
            "weighting_mode": "heuristic",
            "baseline_scores": None,
            "weighting_comparison": None,
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        },
    )()

    with patch(
        "app.api.routes.analysis.AnalysisRepository.get_by_evaluation_id",
        new_callable=AsyncMock,
        return_value=_fake_stored,
    ):
        resp = await client.post(f"/api/v1/analysis/{eval_id_str}/run", headers=_auth(token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["k"] == 3
    assert data["winning_cluster"] == 0


# ── Status endpoint ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_analysis_status_not_started(client: AsyncClient) -> None:
    token = await _register(client, "analysis6@example.com")
    eval_id_str = str(uuid.uuid4())

    with patch(
        "app.api.routes.analysis.AnalysisRepository.get_by_evaluation_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await client.get(f"/api/v1/analysis/{eval_id_str}/status", headers=_auth(token))

    assert resp.status_code == 200
    assert resp.json()["status"] == "not_started"


@pytest.mark.asyncio
async def test_get_analysis_status_done(client: AsyncClient) -> None:
    token = await _register(client, "analysis7@example.com")
    eval_id_str = str(uuid.uuid4())
    fake = type("Analysis", (), {"id": uuid.uuid4()})()

    with patch(
        "app.api.routes.analysis.AnalysisRepository.get_by_evaluation_id",
        new_callable=AsyncMock,
        return_value=fake,
    ):
        resp = await client.get(f"/api/v1/analysis/{eval_id_str}/status", headers=_auth(token))

    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


# ── Logs endpoint ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_analysis_logs(client: AsyncClient) -> None:
    token = await _register(client, "analysis8@example.com")
    eval_id_str = str(uuid.uuid4())

    resp = await client.get(f"/api/v1/analysis/{eval_id_str}/logs", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "lines" in data
    assert "total" in data


# ── Status: running / failed ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_analysis_status_running(client: AsyncClient) -> None:
    token = await _register(client, "analysis10@example.com")
    eval_id_str = str(uuid.uuid4())
    _running.add(eval_id_str)

    with patch(
        "app.api.routes.analysis.AnalysisRepository.get_by_evaluation_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await client.get(f"/api/v1/analysis/{eval_id_str}/status", headers=_auth(token))

    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


@pytest.mark.asyncio
async def test_get_analysis_status_failed(client: AsyncClient) -> None:
    token = await _register(client, "analysis11@example.com")
    eval_id_str = str(uuid.uuid4())
    _failed.add(eval_id_str)

    with patch(
        "app.api.routes.analysis.AnalysisRepository.get_by_evaluation_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await client.get(f"/api/v1/analysis/{eval_id_str}/status", headers=_auth(token))

    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"


# ── Logs with content ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_analysis_logs_with_content(client: AsyncClient) -> None:
    from app.services import log_stream  # noqa: PLC0415

    token = await _register(client, "analysis12@example.com")
    eval_id_str = str(uuid.uuid4())
    log_stream.log(eval_id_str, "[analysis] Embedding 80 responses")
    log_stream.log(eval_id_str, "[analysis] Clustering complete — k=4")

    resp = await client.get(f"/api/v1/analysis/{eval_id_str}/logs", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert any("Embedding" in line for line in data["lines"])

    resp_offset = await client.get(
        f"/api/v1/analysis/{eval_id_str}/logs?offset=1", headers=_auth(token)
    )
    assert len(resp_offset.json()["lines"]) == 1


# ── Background task ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_analysis_background_success() -> None:
    """_run_analysis_background clears _running and creates an analysis record."""
    from unittest.mock import MagicMock  # noqa: PLC0415

    from app.api.routes.analysis import _run_analysis_background  # noqa: PLC0415

    eval_id = uuid.uuid4()
    eid = str(eval_id)
    _running.add(eid)

    from app.models.evaluation import StatusEnum  # noqa: PLC0415

    fake_eval = type(
        "Ev",
        (),
        {"id": eval_id, "status": StatusEnum.done, "rubric_id": uuid.uuid4(), "question": "Q?"},
    )()
    fake_rubric = type("Rb", (), {"criteria": _MOCK_CRITERIA, "doctrine_pack": None})()
    fake_responses = [
        type("MR", (), {"response_text": "t", "model_name": m, "run_index": i})()
        for i, m in enumerate(_FIVE_MODELS * 2)
    ]

    mock_db = MagicMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.api.routes.analysis.AsyncSessionLocal", return_value=mock_cm),
        patch(
            "app.api.routes.analysis.EvaluationRepository",
            return_value=AsyncMock(get_by_id=AsyncMock(return_value=fake_eval)),
        ),
        patch(
            "app.api.routes.analysis.RubricRepository",
            return_value=AsyncMock(
                get_by_id=AsyncMock(return_value=fake_rubric),
                get_by_evaluation_id=AsyncMock(return_value=fake_rubric),
            ),
        ),
        patch(
            "app.api.routes.analysis._load_responses",
            new_callable=AsyncMock,
            return_value=fake_responses,
        ),
        patch(
            "app.api.routes.analysis.analysis_service.run_analysis",
            new_callable=AsyncMock,
            return_value=_MOCK_ANALYSIS_RESULT,
        ),
        patch(
            "app.api.routes.analysis.AnalysisRepository",
            return_value=AsyncMock(create=AsyncMock()),
        ) as mock_analysis_repo,
    ):
        await _run_analysis_background(eval_id)

    assert eid not in _running
    assert eid not in _failed
    mock_analysis_repo.return_value.create.assert_called_once()


@pytest.mark.asyncio
async def test_run_analysis_background_failure() -> None:
    """_run_analysis_background adds to _failed when analysis_service raises."""
    from unittest.mock import MagicMock  # noqa: PLC0415

    from app.api.routes.analysis import _run_analysis_background  # noqa: PLC0415

    eval_id = uuid.uuid4()
    eid = str(eval_id)
    _running.add(eid)

    from app.models.evaluation import StatusEnum  # noqa: PLC0415

    fake_eval = type(
        "Ev",
        (),
        {"id": eval_id, "status": StatusEnum.done, "rubric_id": uuid.uuid4(), "question": "Q?"},
    )()
    fake_rubric = type("Rb", (), {"criteria": _MOCK_CRITERIA})()
    fake_responses = [
        type("MR", (), {"response_text": "t", "model_name": m, "run_index": i})()
        for i, m in enumerate(_FIVE_MODELS)
    ]

    mock_db = MagicMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.api.routes.analysis.AsyncSessionLocal", return_value=mock_cm),
        patch(
            "app.api.routes.analysis.EvaluationRepository",
            return_value=AsyncMock(get_by_id=AsyncMock(return_value=fake_eval)),
        ),
        patch(
            "app.api.routes.analysis.RubricRepository",
            return_value=AsyncMock(
                get_by_id=AsyncMock(return_value=fake_rubric),
                get_by_evaluation_id=AsyncMock(return_value=fake_rubric),
            ),
        ),
        patch(
            "app.api.routes.analysis._load_responses",
            new_callable=AsyncMock,
            return_value=fake_responses,
        ),
        patch(
            "app.api.routes.analysis.analysis_service.run_analysis",
            new_callable=AsyncMock,
            side_effect=RuntimeError("embedding failed"),
        ),
    ):
        await _run_analysis_background(eval_id)

    assert eid not in _running
    assert eid in _failed


# ── Already-running guard ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_analysis_already_running(client: AsyncClient) -> None:
    """POST /run returns 202 with status=running if already in _running."""
    token = await _register(client, "analysis13@example.com")
    eval_id_str = str(uuid.uuid4())
    eval_uuid = uuid.UUID(eval_id_str)

    from app.models.evaluation import StatusEnum  # noqa: PLC0415

    fake_evaluation = type(
        "Ev",
        (),
        {"id": eval_uuid, "status": StatusEnum.done, "rubric_id": uuid.uuid4(), "question": "Q?"},
    )()

    _running.add(eval_id_str)

    with (
        patch(
            "app.api.routes.analysis.AnalysisRepository.get_by_evaluation_id",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.api.routes.analysis.EvaluationRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=fake_evaluation,
        ),
    ):
        resp = await client.post(f"/api/v1/analysis/{eval_id_str}/run", headers=_auth(token))

    assert resp.status_code == 202
    assert resp.json()["status"] == "running"


# ── Idempotent ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_analysis_idempotent(client: AsyncClient) -> None:
    """Second POST returns the existing analysis without re-running."""
    token = await _register(client, "analysis9@example.com")
    eval_id_str = str(uuid.uuid4())
    eval_uuid = uuid.UUID(eval_id_str)

    fake_analysis = type(
        "A",
        (),
        {
            "id": uuid.uuid4(),
            "evaluation_id": eval_uuid,
            "k": 3,
            "clusters": _MOCK_ANALYSIS_RESULT["clusters"],
            "centroid_indices": _MOCK_ANALYSIS_RESULT["centroid_indices"],
            "scores": _MOCK_ANALYSIS_RESULT["scores"],
            "winning_cluster": 0,
            "model_shares": _MOCK_ANALYSIS_RESULT["model_shares"],
            "weighting_mode": "heuristic",
            "baseline_scores": None,
            "weighting_comparison": None,
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        },
    )()

    with patch(
        "app.api.routes.analysis.AnalysisRepository.get_by_evaluation_id",
        new_callable=AsyncMock,
        return_value=fake_analysis,
    ):
        resp = await client.post(f"/api/v1/analysis/{eval_id_str}/run", headers=_auth(token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["k"] == 3
    assert data["winning_cluster"] == 0
    assert "model_shares" in data
    assert "scores" in data
