"""Unit tests for app.services.response_service."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.evaluation import StatusEnum
from app.services.response_service import (
    _generate_single_response,
    generate_responses_background,
    run_evaluation_pipeline,
)


class _FakeEvalRow:
    status: object = None


def _make_db_mock(eval_row: _FakeEvalRow, commit_raises: bool = False):
    """Return an AsyncSessionLocal mock whose context manager yields a fake DB."""
    db = AsyncMock()
    db.add = MagicMock()
    db.get = AsyncMock(return_value=eval_row)
    db.rollback = AsyncMock()

    if commit_raises:
        db.commit = AsyncMock(side_effect=Exception("DB error"))
    else:
        db.commit = AsyncMock()

    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    session_cls = MagicMock(return_value=db)
    return session_cls


# ---------------------------------------------------------------------------
# _generate_single_response
# ---------------------------------------------------------------------------


class TestGenerateSingleResponse:
    @pytest.mark.asyncio
    async def test_returns_text_on_success(self):
        semaphore = asyncio.Semaphore(1)
        eval_id = uuid.uuid4()

        with patch(
            "app.services.github_copilot_client.chat_completion",
            new_callable=AsyncMock,
            return_value="Legal answer text.",
        ):
            model, eid, idx, text, qv = await _generate_single_response(
                eval_id, "What is res judicata?", "openai/gpt-oss-20b", 0, semaphore
            )

        assert model == "openai/gpt-oss-20b"
        assert eid == str(eval_id)
        assert idx == 0
        assert text == "Legal answer text."
        assert qv == "base"

    @pytest.mark.asyncio
    async def test_returns_none_text_on_exception(self):
        semaphore = asyncio.Semaphore(1)
        eval_id = uuid.uuid4()

        with patch(
            "app.services.github_copilot_client.chat_completion",
            new_callable=AsyncMock,
            side_effect=Exception("API error"),
        ):
            model, eid, idx, text, qv = await _generate_single_response(
                eval_id, "What is res judicata?", "openai/gpt-oss-20b", 0, semaphore
            )

        assert model == "openai/gpt-oss-20b"
        assert text is None
        assert qv == "base"

    @pytest.mark.asyncio
    async def test_run_index_preserved(self):
        semaphore = asyncio.Semaphore(1)
        eval_id = uuid.uuid4()

        with patch(
            "app.services.github_copilot_client.chat_completion",
            new_callable=AsyncMock,
            return_value="answer",
        ):
            _, _, idx, _, _ = await _generate_single_response(
                eval_id, "question", "openai/gpt-oss-20b", 42, semaphore
            )

        assert idx == 42

    @pytest.mark.asyncio
    async def test_custom_question_version_returned(self):
        semaphore = asyncio.Semaphore(1)
        eval_id = uuid.uuid4()

        with patch(
            "app.services.github_copilot_client.chat_completion",
            new_callable=AsyncMock,
            return_value="variation answer",
        ):
            _, _, _, _, qv = await _generate_single_response(
                eval_id,
                "variation q?",
                "openai/gpt-oss-20b",
                0,
                semaphore,
                question_version="variation",
            )

        assert qv == "variation"


# ---------------------------------------------------------------------------
# generate_responses_background
# ---------------------------------------------------------------------------


class TestGenerateResponsesBackground:
    @pytest.mark.asyncio
    async def test_marks_evaluation_done_on_success(self):
        eval_id = uuid.uuid4()
        eval_row = _FakeEvalRow()
        session_cls = _make_db_mock(eval_row)

        with (
            patch(
                "app.services.github_copilot_client.chat_completion",
                new_callable=AsyncMock,
                return_value="answer",
            ),
            patch("app.services.response_service.AsyncSessionLocal", session_cls),
        ):
            await generate_responses_background(eval_id, "question?", ["openai/gpt-oss-20b"])

        assert eval_row.status == StatusEnum.done

    @pytest.mark.asyncio
    async def test_marks_evaluation_failed_on_db_error(self):
        eval_id = uuid.uuid4()
        eval_row = _FakeEvalRow()

        commit_call = 0
        db = AsyncMock()
        db.add = MagicMock()
        db.get = AsyncMock(return_value=eval_row)
        db.rollback = AsyncMock()

        async def _commit():
            nonlocal commit_call
            commit_call += 1
            if commit_call == 2:
                raise Exception("disk full")

        db.commit = _commit
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        session_cls = MagicMock(return_value=db)

        with (
            patch(
                "app.services.github_copilot_client.chat_completion",
                new_callable=AsyncMock,
                return_value="answer",
            ),
            patch("app.services.response_service.AsyncSessionLocal", session_cls),
        ):
            await generate_responses_background(eval_id, "question?", ["openai/gpt-oss-20b"])

        assert eval_row.status == StatusEnum.failed

    @pytest.mark.asyncio
    async def test_skips_exception_results_gracefully(self):
        """gather() return_exceptions=True — Exception objects in results are skipped."""
        eval_id = uuid.uuid4()
        eval_row = _FakeEvalRow()
        session_cls = _make_db_mock(eval_row)

        # chat_completion always raises → all results will be None-text tuples
        with (
            patch(
                "app.services.github_copilot_client.chat_completion",
                new_callable=AsyncMock,
                side_effect=Exception("fail"),
            ),
            patch("app.services.response_service.AsyncSessionLocal", session_cls),
        ):
            await generate_responses_background(eval_id, "question?", ["openai/gpt-oss-20b"])

        # Should still mark as done (no crash)
        assert eval_row.status == StatusEnum.done

    @pytest.mark.asyncio
    async def test_with_variation_question_marks_done(self):
        """When variation_question is provided, both passes complete and eval is marked done."""
        eval_id = uuid.uuid4()
        eval_row = _FakeEvalRow()
        session_cls = _make_db_mock(eval_row)

        with (
            patch(
                "app.services.github_copilot_client.chat_completion",
                new_callable=AsyncMock,
                return_value="answer",
            ),
            patch("app.services.response_service.AsyncSessionLocal", session_cls),
        ):
            await generate_responses_background(
                eval_id,
                "base question?",
                ["openai/gpt-oss-20b"],
                variation_question="variation question?",
            )

        assert eval_row.status == StatusEnum.done


# ---------------------------------------------------------------------------
# run_evaluation_pipeline
# ---------------------------------------------------------------------------


class TestRunEvaluationPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_forwards_variation_question(self):
        """run_evaluation_pipeline passes variation_question to _generate_comparison_responses."""
        eval_id = uuid.uuid4()
        eval_row = _FakeEvalRow()
        session_cls = _make_db_mock(eval_row)

        with (
            patch(
                "app.services.github_copilot_client.chat_completion",
                new_callable=AsyncMock,
                return_value="answer",
            ),
            patch("app.services.response_service.AsyncSessionLocal", session_cls),
        ):
            await run_evaluation_pipeline(
                eval_id,
                "base question?",
                ["openai/gpt-oss-20b"],
                variation_question="variation q?",
            )

        assert eval_row.status == StatusEnum.done

    @pytest.mark.asyncio
    async def test_pipeline_without_variation_question_still_works(self):
        """run_evaluation_pipeline works with no variation_question (backward compat)."""
        eval_id = uuid.uuid4()
        eval_row = _FakeEvalRow()
        session_cls = _make_db_mock(eval_row)

        with (
            patch(
                "app.services.github_copilot_client.chat_completion",
                new_callable=AsyncMock,
                return_value="answer",
            ),
            patch("app.services.response_service.AsyncSessionLocal", session_cls),
        ):
            await run_evaluation_pipeline(eval_id, "question?", ["openai/gpt-oss-20b"])

        assert eval_row.status == StatusEnum.done
