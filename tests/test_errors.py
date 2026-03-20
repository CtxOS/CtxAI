import asyncio

import pytest
from ctxai.helpers.errors import error_text
from ctxai.helpers.errors import format_error
from ctxai.helpers.errors import handle_error
from ctxai.helpers.errors import HandledException
from ctxai.helpers.errors import InterventionException
from ctxai.helpers.errors import RepairableException


class TestErrors:
    def test_error_text_simple(self):
        e = ValueError("test error")
        result = error_text(e)
        assert result == "test error"

    def test_error_text_empty(self):
        e = ValueError("")
        result = error_text(e)
        assert result == ""

    def test_handle_error_cancelled_error(self):
        e = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            handle_error(e)

    def test_handle_error_other_exception(self):
        e = ValueError("test")
        # Should not raise
        handle_error(e)

    def test_format_error_basic(self):
        e = ValueError("test error")
        result = format_error(e)
        assert "ValueError" in result
        assert "test error" in result

    def test_format_error_with_traceback(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            result = format_error(e)
            assert "ValueError" in result

    def test_format_error_position_top(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            result = format_error(e, error_message_position="top")
            assert result.startswith("ValueError")

    def test_format_error_position_bottom(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            result = format_error(e, error_message_position="bottom")
            assert "ValueError" in result
            assert "test error" in result

    def test_format_error_position_none(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            result = format_error(e, error_message_position="none")
            assert "test error" not in result or "ValueError" in result

    def test_format_error_zero_entries(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            result = format_error(e, start_entries=0, end_entries=0)
            assert "test error" in result

    def test_format_error_custom_entries(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            result = format_error(e, start_entries=5, end_entries=5)
            assert result is not None

    def test_repairable_exception(self):
        e = RepairableException("repairable error")
        assert isinstance(e, Exception)
        assert str(e) == "repairable error"

    def test_intervention_exception(self):
        e = InterventionException("user intervened")
        assert isinstance(e, Exception)
        assert str(e) == "user intervened"

    def test_handled_exception(self):
        e = HandledException("handled error")
        assert isinstance(e, Exception)
        assert str(e) == "handled error"
