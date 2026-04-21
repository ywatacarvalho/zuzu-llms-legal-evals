import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, email: str) -> str:
    resp = await client.post("/api/v1/auth/register", json={"email": email, "password": "pass123"})
    return resp.json()["access_token"]


async def _create_case(client: AsyncClient, token: str) -> str:
    with patch("app.services.case_service.pdfplumber") as mp:
        mp.open.return_value.__enter__.return_value.pages = []
        resp = await client.post(
            "/api/v1/cases",
            files={"file": ("c.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
            data={"title": "TestCase"},
            headers=_auth(token),
        )
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# POST /rubrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_rubric_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/rubrics", json={})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_rubric_case_not_found(client: AsyncClient) -> None:
    token = await _register(client, "rubric_c1@example.com")
    resp = await client.post(
        "/api/v1/rubrics",
        json={
            "case_id": "00000000-0000-0000-0000-000000000000",
            "question": "What is the applicable legal standard here?",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_rubric_success(client: AsyncClient) -> None:
    token = await _register(client, "rubric_c2@example.com")
    case_id = await _create_case(client, token)

    with patch(
        "app.api.routes.rubrics._build_rubric_background",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            "/api/v1/rubrics",
            json={
                "case_id": case_id,
                "question": "What is the applicable legal standard here?",
            },
            headers=_auth(token),
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "building"
    assert data["case_id"] == case_id
    assert data["question"] == "What is the applicable legal standard here?"


# ---------------------------------------------------------------------------
# GET /rubrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_rubrics_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/rubrics")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_rubrics(client: AsyncClient) -> None:
    token = await _register(client, "rubric_l1@example.com")
    resp = await client.get("/api/v1/rubrics", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# GET /rubrics/frozen
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_frozen_rubrics_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/rubrics/frozen")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_frozen_rubrics(client: AsyncClient) -> None:
    token = await _register(client, "rubric_f1@example.com")
    resp = await client.get("/api/v1/rubrics/frozen", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# GET /rubrics/{rubric_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_rubric_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/rubrics/{uuid.uuid4()}")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_rubric_not_found(client: AsyncClient) -> None:
    token = await _register(client, "rubric_get1@example.com")
    resp = await client.get(
        f"/api/v1/rubrics/{uuid.uuid4()}",
        headers=_auth(token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /rubrics/{rubric_id}/logs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_rubric_logs_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/rubrics/{uuid.uuid4()}/logs")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_rubric_logs_returns_empty(client: AsyncClient) -> None:
    token = await _register(client, "rubric_log1@example.com")
    rid = "00000000-0000-0000-0000-aaaaaaaaaaaa"
    resp = await client.get(f"/api/v1/rubrics/{rid}/logs", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["lines"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_rubric_logs_with_offset(client: AsyncClient) -> None:
    from app.services import log_stream

    rid = "00000000-0000-0000-0000-bbbbbbbbbbbb"
    log_stream.log(rid, "line 1")
    log_stream.log(rid, "line 2")
    log_stream.log(rid, "line 3")

    token = await _register(client, "rubric_log2@example.com")
    resp = await client.get(f"/api/v1/rubrics/{rid}/logs?offset=1", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["lines"]) == 2


# ---------------------------------------------------------------------------
# POST /rubrics/{rubric_id}/stop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_rubric_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(f"/api/v1/rubrics/{uuid.uuid4()}/stop")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_stop_rubric_not_found(client: AsyncClient) -> None:
    token = await _register(client, "rubric_s1@example.com")
    resp = await client.post(
        f"/api/v1/rubrics/{uuid.uuid4()}/stop",
        headers=_auth(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stop_rubric_success(client: AsyncClient) -> None:
    token = await _register(client, "rubric_s2@example.com")
    case_id = await _create_case(client, token)

    with patch(
        "app.api.routes.rubrics._build_rubric_background",
        new_callable=AsyncMock,
    ):
        create_resp = await client.post(
            "/api/v1/rubrics",
            json={
                "case_id": case_id,
                "question": "What is the applicable legal standard here?",
            },
            headers=_auth(token),
        )
    rubric_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/rubrics/{rubric_id}/stop",
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"


# ---------------------------------------------------------------------------
# GET /rubrics/evaluation/{evaluation_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_rubric_by_evaluation_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/rubrics/evaluation/{uuid.uuid4()}")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_rubric_by_evaluation_not_found(client: AsyncClient) -> None:
    token = await _register(client, "rubric_eval1@example.com")
    resp = await client.get(
        f"/api/v1/rubrics/evaluation/{uuid.uuid4()}",
        headers=_auth(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_rubric_by_evaluation_returns_rubric(client: AsyncClient) -> None:
    token = await _register(client, "rubric_eval2@example.com")
    eval_uuid = uuid.uuid4()

    _MOCK_CRITERIA = [
        {
            "id": "accuracy",
            "name": "Accuracy",
            "description": "Factual correctness.",
            "weight": 0.5,
        },
        {"id": "reasoning", "name": "Reasoning", "description": "Legal reasoning.", "weight": 0.5},
    ]

    fake_rubric = type(
        "Rubric",
        (),
        {
            "id": uuid.uuid4(),
            "evaluation_id": eval_uuid,
            "case_id": None,
            "question": None,
            "status": "frozen",
            "criteria": _MOCK_CRITERIA,
            "raw_response": None,
            "is_frozen": True,
            "conditioning_sample": [],
            "decomposition_tree": {},
            "refinement_passes": [],
            "stopping_metadata": {},
            "setup_responses": None,
            "strong_reference_text": None,
            "weak_reference_text": None,
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        },
    )()

    with patch(
        "app.api.routes.rubrics.RubricRepository.get_by_evaluation_id",
        new_callable=AsyncMock,
        return_value=fake_rubric,
    ):
        resp = await client.get(
            f"/api/v1/rubrics/evaluation/{eval_uuid}",
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["evaluation_id"] == str(eval_uuid)
    assert data["is_frozen"] is True
    assert len(data["criteria"]) == 2


# ---------------------------------------------------------------------------
# POST /rubrics/{rubric_id}/approve  (Phase 8 HITL gate tests T8.16 -- T8.22)
# ---------------------------------------------------------------------------

_MOCK_CRITERIA = [
    {"id": "accuracy", "name": "Accuracy", "description": "Factual correctness.", "weight": 0.6},
    {"id": "reasoning", "name": "Reasoning", "description": "Legal reasoning.", "weight": 0.4},
]

_NOW = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)


def _fake_awaiting_rubric(rubric_id: uuid.UUID) -> object:
    """Build a minimal fake Rubric object in 'awaiting_review' state."""
    return type(
        "Rubric",
        (),
        {
            "id": rubric_id,
            "evaluation_id": None,
            "case_id": uuid.uuid4(),
            "question": "Is this oral promise enforceable?",
            "status": "building",
            "is_frozen": False,
            "criteria": None,
            "raw_response": None,
            "conditioning_sample": None,
            "decomposition_tree": None,
            "refinement_passes": None,
            "stopping_metadata": None,
            "setup_responses": None,
            "strong_reference_text": None,
            "weak_reference_text": "weak text",
            "screening_result": None,
            "source_extraction": {"clean_legal_issue": "q"},
            "routing_metadata": {"selected_pack": "pack_10", "confidence": "high"},
            "doctrine_pack": "pack_10",
            "gold_packet_mapping": None,
            "predicted_failure_modes": None,
            "gold_answer": "Gold answer text.",
            "self_audit_result": {"classification": "Ready"},
            "fi_status": "awaiting_review",
            "fi_stream_id": str(uuid.uuid4()),
            "review_notes": None,
            "generated_question": None,
            "question_analysis": None,
            "created_at": _NOW,
            "updated_at": _NOW,
        },
    )()


@pytest.mark.asyncio
async def test_approve_rubric_requires_auth(client: AsyncClient) -> None:
    """T8.16 -- approve endpoint requires authentication."""
    resp = await client.post(
        f"/api/v1/rubrics/{uuid.uuid4()}/approve",
        json={"action": "approve"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_approve_rubric_not_found(client: AsyncClient) -> None:
    """T8.17 -- returns 404 when rubric does not exist."""
    token = await _register(client, "approve_nf@example.com")
    with patch(
        "app.api.routes.rubrics.RubricRepository.get_by_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{uuid.uuid4()}/approve",
            json={"action": "approve"},
            headers=_auth(token),
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_rubric_wrong_status_returns_409(client: AsyncClient) -> None:
    """T8.18 -- returns 409 when rubric is not in awaiting_review state."""
    token = await _register(client, "approve_409@example.com")
    rid = uuid.uuid4()
    fake = _fake_awaiting_rubric(rid)
    fake.fi_status = "completed"  # not awaiting_review

    with patch(
        "app.api.routes.rubrics.RubricRepository.get_by_id",
        new_callable=AsyncMock,
        return_value=fake,
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/approve",
            json={"action": "approve"},
            headers=_auth(token),
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_approve_action_launches_phase_b(client: AsyncClient) -> None:
    """T8.19 -- approve action returns 202 and schedules Phase B."""
    token = await _register(client, "approve_ok@example.com")
    rid = uuid.uuid4()

    with (
        patch(
            "app.api.routes.rubrics.RubricRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=_fake_awaiting_rubric(rid),
        ),
        patch(
            "app.api.routes.rubrics.RubricRepository.approve_fi",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.routes.rubrics._build_rubric_phase_b_background",
            new_callable=AsyncMock,
        ),
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/approve",
            json={"action": "approve", "notes": "Looks good"},
            headers=_auth(token),
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "approved"
    assert data["rubric_id"] == str(rid)


@pytest.mark.asyncio
async def test_reject_action_marks_rubric_failed(client: AsyncClient) -> None:
    """T8.20 -- reject action returns 202 with status=rejected."""
    token = await _register(client, "reject_ok@example.com")
    rid = uuid.uuid4()

    with (
        patch(
            "app.api.routes.rubrics.RubricRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=_fake_awaiting_rubric(rid),
        ),
        patch(
            "app.api.routes.rubrics.RubricRepository.approve_fi",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.routes.rubrics.RubricRepository.set_status",
            new_callable=AsyncMock,
        ),
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/approve",
            json={"action": "reject", "notes": "Too many red flags"},
            headers=_auth(token),
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "rejected"


@pytest.mark.asyncio
async def test_reroute_action_restarts_pipeline(client: AsyncClient) -> None:
    """T8.21 -- reroute action returns 202 and restarts the full pipeline."""
    token = await _register(client, "reroute_ok@example.com")
    rid = uuid.uuid4()
    fake = _fake_awaiting_rubric(rid)

    with (
        patch(
            "app.api.routes.rubrics.RubricRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=fake,
        ),
        patch(
            "app.api.routes.rubrics.RubricRepository.reset_for_rerun",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.routes.rubrics.RubricRepository.approve_fi",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.routes.rubrics.CaseRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.api.routes.rubrics._build_rubric_background",
            new_callable=AsyncMock,
        ),
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/approve",
            json={"action": "reroute", "reroute_pack": "pack_7"},
            headers=_auth(token),
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "rerouting"


@pytest.mark.asyncio
async def test_approve_invalid_action_returns_422(client: AsyncClient) -> None:
    """T8.22 -- unknown action returns 422."""
    token = await _register(client, "approve_bad@example.com")
    resp = await client.post(
        f"/api/v1/rubrics/{uuid.uuid4()}/approve",
        json={"action": "invalid_action"},
        headers=_auth(token),
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /rubrics/{rubric_id}/validate-question  (Phase 10)
# ---------------------------------------------------------------------------


def _fake_rubric_with_extraction(rubric_id: uuid.UUID, *, has_extraction: bool = True) -> object:
    """Minimal fake Rubric with optional source_extraction for Phase 10 tests."""
    return type(
        "Rubric",
        (),
        {
            "id": rubric_id,
            "evaluation_id": None,
            "case_id": None,
            "question": "Is the oral promise enforceable? Analyze.",
            "status": "frozen",
            "is_frozen": True,
            "criteria": None,
            "raw_response": None,
            "conditioning_sample": None,
            "decomposition_tree": None,
            "refinement_passes": None,
            "stopping_metadata": None,
            "setup_responses": None,
            "strong_reference_text": None,
            "weak_reference_text": None,
            "screening_result": None,
            "source_extraction": {"clean_legal_issue": "q"} if has_extraction else None,
            "routing_metadata": None,
            "doctrine_pack": "pack_20",
            "gold_packet_mapping": {"governing_rule": "SOF land"} if has_extraction else None,
            "predicted_failure_modes": None,
            "gold_answer": None,
            "self_audit_result": None,
            "fi_status": None,
            "fi_stream_id": None,
            "review_notes": None,
            "generated_question": None,
            "question_analysis": None,
            "created_at": _NOW,
            "updated_at": _NOW,
        },
    )()


@pytest.mark.asyncio
async def test_validate_question_returns_200_with_checklist(client: AsyncClient) -> None:
    """T10.12 -- POST /{id}/validate-question returns 200 with checklist dict."""

    token = await _register(client, "vq_ok@example.com")
    rid = uuid.uuid4()
    checklist_resp = {
        "checks": [{"item": "Neutral call", "pass": True, "note": "OK"}],
        "red_flags": [],
        "overall_pass": True,
        "suggestions": [],
    }

    with (
        patch(
            "app.api.routes.rubrics.RubricRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=_fake_rubric_with_extraction(rid),
        ),
        patch(
            "app.services.rubric_service.validate_question",
            new_callable=AsyncMock,
            return_value=checklist_resp,
        ),
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/validate-question",
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "checks" in data
    assert "overall_pass" in data


@pytest.mark.asyncio
async def test_validate_question_422_when_no_source_extraction(client: AsyncClient) -> None:
    """T10.13 -- POST /{id}/validate-question returns 422 when rubric has no source_extraction."""
    token = await _register(client, "vq_noext@example.com")
    rid = uuid.uuid4()

    with patch(
        "app.api.routes.rubrics.RubricRepository.get_by_id",
        new_callable=AsyncMock,
        return_value=_fake_rubric_with_extraction(rid, has_extraction=False),
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/validate-question",
            headers=_auth(token),
        )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /rubrics/{rubric_id}/generate-question  (Phase 10)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_question_returns_200_with_question(client: AsyncClient) -> None:
    """T10.14 -- POST /{id}/generate-question returns 200 with generated question."""
    token = await _register(client, "gq_ok@example.com")
    rid = uuid.uuid4()
    gen_resp = {
        "question": "Is the agreement enforceable? Analyze.",
        "internal_notes": {
            "target_doctrine": "SOF land",
            "likely_distractors": [],
            "source_fidelity_notes": "OK",
        },
    }

    with (
        patch(
            "app.api.routes.rubrics.RubricRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=_fake_rubric_with_extraction(rid),
        ),
        patch(
            "app.services.rubric_service.generate_question",
            new_callable=AsyncMock,
            return_value=gen_resp,
        ),
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/generate-question",
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "question" in data
    assert data["question"]


@pytest.mark.asyncio
async def test_generate_question_422_when_no_gold_packet_mapping(client: AsyncClient) -> None:
    """T10.15 -- POST /{id}/generate-question returns 422 when rubric has no gold_packet_mapping."""
    token = await _register(client, "gq_nomap@example.com")
    rid = uuid.uuid4()

    with patch(
        "app.api.routes.rubrics.RubricRepository.get_by_id",
        new_callable=AsyncMock,
        return_value=_fake_rubric_with_extraction(rid, has_extraction=False),
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/generate-question",
            headers=_auth(token),
        )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Phase 12: POST /rubrics/{rubric_id}/extract-only
# ---------------------------------------------------------------------------


def _fake_rubric_for_mode_a(
    rubric_id: uuid.UUID,
    *,
    has_case: bool = True,
) -> object:
    """Minimal fake Rubric for Mode A tests — may or may not have a linked case."""
    return type(
        "Rubric",
        (),
        {
            "id": rubric_id,
            "evaluation_id": None,
            "case_id": uuid.uuid4() if has_case else None,
            "question": "Is the oral promise enforceable? Analyze.",
            "status": "frozen",
            "is_frozen": True,
            "criteria": None,
            "raw_response": None,
            "conditioning_sample": None,
            "decomposition_tree": None,
            "refinement_passes": None,
            "stopping_metadata": None,
            "setup_responses": None,
            "strong_reference_text": None,
            "weak_reference_text": None,
            "screening_result": None,
            "source_extraction": None,
            "routing_metadata": None,
            "doctrine_pack": None,
            "gold_packet_mapping": None,
            "predicted_failure_modes": None,
            "gold_answer": None,
            "self_audit_result": None,
            "fi_status": None,
            "fi_stream_id": None,
            "review_notes": None,
            "generated_question": None,
            "question_analysis": None,
            "created_at": _NOW,
            "updated_at": _NOW,
        },
    )()


@pytest.mark.asyncio
async def test_extract_only_requires_auth(client: AsyncClient) -> None:
    """T12.10 -- POST /{id}/extract-only requires authentication."""
    resp = await client.post(f"/api/v1/rubrics/{uuid.uuid4()}/extract-only")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_extract_only_not_found(client: AsyncClient) -> None:
    """T12.10b -- POST /{id}/extract-only returns 404 when rubric missing."""
    token = await _register(client, "ea_nf@example.com")
    with patch(
        "app.api.routes.rubrics.RubricRepository.get_by_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{uuid.uuid4()}/extract-only",
            headers=_auth(token),
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_extract_only_422_when_no_case_text(client: AsyncClient) -> None:
    """T12.11 -- POST /{id}/extract-only returns 422 when no case text available."""
    token = await _register(client, "ea_nocase@example.com")
    rid = uuid.uuid4()
    with (
        patch(
            "app.api.routes.rubrics.RubricRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=_fake_rubric_for_mode_a(rid, has_case=False),
        ),
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/extract-only",
            headers=_auth(token),
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_only_returns_200_with_keys(client: AsyncClient) -> None:
    """T12.12 -- POST /{id}/extract-only returns 200 with extraction keys."""
    token = await _register(client, "ea_ok@example.com")
    rid = uuid.uuid4()
    fake_rubric = _fake_rubric_for_mode_a(rid, has_case=True)
    fake_case = type("Case", (), {"raw_text": "Buyer made oral promise to purchase land."})()
    mode_a_result = {
        "screening_result": {"rating": "strong_lead"},
        "source_extraction": {"clean_legal_issue": "SOF writing"},
        "routing_metadata": {"pack_id": "pack_10"},
        "doctrine_pack": {"name": "Land contracts"},
    }

    with (
        patch(
            "app.api.routes.rubrics.RubricRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=fake_rubric,
        ),
        patch(
            "app.api.routes.rubrics.CaseRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=fake_case,
        ),
        patch(
            "app.services.rubric_service.run_mode_a",
            new_callable=AsyncMock,
            return_value=mode_a_result,
        ),
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/extract-only",
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "source_extraction" in data
    assert "doctrine_pack" in data


# ---------------------------------------------------------------------------
# Phase 12: POST /rubrics/{rubric_id}/compare-draft
# ---------------------------------------------------------------------------

_FAKE_EXTRACTION = {"clean_legal_issue": "SOF land writing requirement", "jurisdiction_forum": "CA"}
_FAKE_PACK = {"name": "Land contracts"}


def _fake_rubric_with_source(rubric_id: uuid.UUID, *, has_extraction: bool = True) -> object:
    return type(
        "Rubric",
        (),
        {
            "id": rubric_id,
            "evaluation_id": None,
            "case_id": None,
            "question": "Is it enforceable?",
            "status": "frozen",
            "is_frozen": True,
            "criteria": None,
            "raw_response": None,
            "conditioning_sample": None,
            "decomposition_tree": None,
            "refinement_passes": None,
            "stopping_metadata": None,
            "setup_responses": None,
            "strong_reference_text": None,
            "weak_reference_text": None,
            "screening_result": None,
            "source_extraction": _FAKE_EXTRACTION if has_extraction else None,
            "routing_metadata": None,
            "doctrine_pack": _FAKE_PACK,
            "gold_packet_mapping": None,
            "predicted_failure_modes": None,
            "gold_answer": None,
            "self_audit_result": None,
            "fi_status": None,
            "fi_stream_id": None,
            "review_notes": None,
            "generated_question": None,
            "question_analysis": None,
            "created_at": _NOW,
            "updated_at": _NOW,
        },
    )()


@pytest.mark.asyncio
async def test_compare_draft_requires_auth(client: AsyncClient) -> None:
    """T12.13 -- POST /{id}/compare-draft requires authentication."""
    resp = await client.post(
        f"/api/v1/rubrics/{uuid.uuid4()}/compare-draft",
        json={"draft_text": "Some draft answer."},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_compare_draft_422_when_no_source_extraction(client: AsyncClient) -> None:
    """T12.14 -- POST /{id}/compare-draft returns 422 when source_extraction missing."""
    token = await _register(client, "cd_noext@example.com")
    rid = uuid.uuid4()
    with patch(
        "app.api.routes.rubrics.RubricRepository.get_by_id",
        new_callable=AsyncMock,
        return_value=_fake_rubric_with_source(rid, has_extraction=False),
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/compare-draft",
            json={"draft_text": "The oral promise is unenforceable under SOF."},
            headers=_auth(token),
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_compare_draft_returns_200_with_eight_headings(client: AsyncClient) -> None:
    """T12.15 -- POST /{id}/compare-draft returns 200 with 8-heading comparison."""
    token = await _register(client, "cd_ok@example.com")
    rid = uuid.uuid4()
    comparison = {
        "source_benchmark_alignment": "OK",
        "controlling_doctrine_match": "OK",
        "gate_order_correctness": "OK",
        "trigger_test_accuracy": "OK",
        "exception_substitute_mapping": "OK",
        "fallback_doctrine_treatment": "OK",
        "factual_fidelity": "OK",
        "provenance_discipline": "OK",
    }

    with (
        patch(
            "app.api.routes.rubrics.RubricRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=_fake_rubric_with_source(rid),
        ),
        patch(
            "app.services.rubric_service.compare_draft_to_source",
            new_callable=AsyncMock,
            return_value=comparison,
        ),
    ):
        resp = await client.post(
            f"/api/v1/rubrics/{rid}/compare-draft",
            json={"draft_text": "The oral promise is unenforceable under SOF."},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "source_benchmark_alignment" in data
    assert "provenance_discipline" in data
