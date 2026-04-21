"""Unit tests for app.services.log_stream."""

from app.services import log_stream as ls


class TestLogStream:
    def setup_method(self):
        # Reset the internal store before each test by clearing the key
        ls._store.clear()

    def test_log_appends_line(self):
        ls.log("eval-1", "hello")
        lines = ls.get_lines("eval-1")
        assert len(lines) == 1
        assert "hello" in lines[0]

    def test_get_lines_with_offset(self):
        ls.log("eval-2", "line A")
        ls.log("eval-2", "line B")
        ls.log("eval-2", "line C")
        lines = ls.get_lines("eval-2", offset=1)
        assert len(lines) == 2
        assert "line B" in lines[0]
        assert "line C" in lines[1]

    def test_total_returns_count(self):
        ls.log("eval-3", "x")
        ls.log("eval-3", "y")
        assert ls.total("eval-3") == 2

    def test_total_returns_zero_for_unknown_id(self):
        assert ls.total("nonexistent") == 0

    def test_get_lines_returns_empty_for_unknown_id(self):
        assert ls.get_lines("nonexistent") == []

    def test_lines_are_timestamped(self):
        ls.log("eval-4", "test message")
        line = ls.get_lines("eval-4")[0]
        # Timestamp format is [HH:MM:SS]
        assert line.startswith("[")
        assert "]" in line

    def test_multiple_evaluations_are_isolated(self):
        ls.log("eval-a", "message for a")
        ls.log("eval-b", "message for b")
        assert ls.total("eval-a") == 1
        assert ls.total("eval-b") == 1
        assert "message for a" in ls.get_lines("eval-a")[0]
        assert "message for b" in ls.get_lines("eval-b")[0]
