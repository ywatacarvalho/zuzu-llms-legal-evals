"""Unit tests for app.services.frank_service -- Phase 8: run_self_audit."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.frank_service import run_self_audit

_GOLD_ANSWER = (
    "BOTTOM LINE: The oral promise is likely unenforceable.\n"
    "CONTROLLING DOCTRINE: Statute of Frauds.\n"
)
_SOURCE_EXTRACTION = {
    "clean_legal_issue": "Whether an oral promise is enforceable",
    "black_letter_rule": "SoF requires writing for land transfers",
}
_ROUTING_METADATA = {
    "selected_pack": "pack_10",
    "confidence": "high",
}


# ---------------------------------------------------------------------------
# Phase 8: run_self_audit
# ---------------------------------------------------------------------------


class TestRunSelfAudit:
    """T8.6 -- T8.10: run_self_audit() service function tests."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_classification(self):
        """T8.6 -- run_self_audit returns a dict containing 'classification'."""
        audit_payload = json.dumps(
            {
                "fast_triage": {
                    "1": {"pass": True, "notes": "ok"},
                    "2": {"pass": True, "notes": "ok"},
                    "3": {"pass": True, "notes": "ok"},
                    "4": {"pass": True, "notes": "ok"},
                },
                "red_flags": [],
                "release_check": {"all_pass": True, "failures": []},
                "classification": "Ready",
            }
        )
        with patch(
            "app.services.frank_service.chat_completion",
            new_callable=AsyncMock,
            return_value=audit_payload,
        ):
            result = await run_self_audit(
                stream_id=None,
                gold_answer=_GOLD_ANSWER,
                source_extraction=_SOURCE_EXTRACTION,
                doctrine_pack="pack_10",
                routing_metadata=_ROUTING_METADATA,
            )

        assert "classification" in result
        assert result["classification"] == "Ready"

    @pytest.mark.asyncio
    async def test_logs_critical_for_needs_rerouting(self):
        """T8.7 -- classification 'Needs rerouting' is logged as CRITICAL."""
        audit_payload = json.dumps(
            {
                "fast_triage": {},
                "red_flags": ["Wrong doctrine pack appears to be driving the answer"],
                "release_check": {"all_pass": False, "failures": ["Pack does not fit issue"]},
                "classification": "Needs rerouting",
            }
        )
        log_calls: list[str] = []

        def _fake_log(stream_id: str, msg: str) -> None:
            log_calls.append(msg)

        with (
            patch(
                "app.services.frank_service.chat_completion",
                new_callable=AsyncMock,
                return_value=audit_payload,
            ),
            patch("app.services.frank_service.log_stream.log", side_effect=_fake_log),
        ):
            result = await run_self_audit(
                stream_id="test-stream",
                gold_answer=_GOLD_ANSWER,
                source_extraction=_SOURCE_EXTRACTION,
                doctrine_pack="pack_10",
                routing_metadata=_ROUTING_METADATA,
            )

        assert result["classification"] == "Needs rerouting"
        assert any("CRITICAL" in msg for msg in log_calls)

    @pytest.mark.asyncio
    async def test_logs_warning_for_needs_major_rewrite(self):
        """T8.8 -- classification 'Needs major rewrite' is logged as WARNING."""
        audit_payload = json.dumps(
            {
                "fast_triage": {},
                "red_flags": ["Controlling doctrine omitted"],
                "release_check": {"all_pass": False, "failures": ["doctrine missing"]},
                "classification": "Needs major rewrite",
            }
        )
        log_calls: list[str] = []

        def _fake_log(stream_id: str, msg: str) -> None:
            log_calls.append(msg)

        with (
            patch(
                "app.services.frank_service.chat_completion",
                new_callable=AsyncMock,
                return_value=audit_payload,
            ),
            patch("app.services.frank_service.log_stream.log", side_effect=_fake_log),
        ):
            result = await run_self_audit(
                stream_id="test-stream",
                gold_answer=_GOLD_ANSWER,
                source_extraction=_SOURCE_EXTRACTION,
                doctrine_pack="pack_10",
                routing_metadata=_ROUTING_METADATA,
            )

        assert result["classification"] == "Needs major rewrite"
        assert any("WARNING" in msg for msg in log_calls)

    @pytest.mark.asyncio
    async def test_handles_invalid_json_gracefully(self):
        """T8.9 -- invalid JSON from LLM sets classification to 'Needs targeted revision'."""
        with patch(
            "app.services.frank_service.chat_completion",
            new_callable=AsyncMock,
            return_value="not valid json {{{{",
        ):
            result = await run_self_audit(
                stream_id=None,
                gold_answer=_GOLD_ANSWER,
                source_extraction=_SOURCE_EXTRACTION,
                doctrine_pack="pack_10",
                routing_metadata=_ROUTING_METADATA,
            )

        assert "classification" in result
        assert result["classification"] == "Needs targeted revision"
        assert "parse_error" in result

    @pytest.mark.asyncio
    async def test_does_not_log_when_stream_id_is_none(self):
        """T8.10 -- no log calls when stream_id is None."""
        audit_payload = json.dumps(
            {
                "fast_triage": {},
                "red_flags": [],
                "release_check": {"all_pass": True, "failures": []},
                "classification": "Ready",
            }
        )
        with (
            patch(
                "app.services.frank_service.chat_completion",
                new_callable=AsyncMock,
                return_value=audit_payload,
            ),
            patch("app.services.frank_service.log_stream.log") as mock_log,
        ):
            await run_self_audit(
                stream_id=None,
                gold_answer=_GOLD_ANSWER,
                source_extraction=_SOURCE_EXTRACTION,
                doctrine_pack="pack_10",
                routing_metadata=_ROUTING_METADATA,
            )

        mock_log.assert_not_called()
