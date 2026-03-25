"""Tests for ValidatorAgent adversarial mandate enforcement (improvement ①).

Tests that pass verdicts are overridden to fail when failure_candidates < 3.
"""

import pytest

from app.core.executor.generic_agent import enforce_adversarial_mandate


class TestEnforceAdversarialMandate:
    """Test enforce_adversarial_mandate function directly."""

    def test_pass_with_3_candidates_stays_pass(self):
        """pass + 3 failure_candidates → pass (no override)."""
        report = {
            "validation_result": "pass",
            "failure_candidates": ["issue A", "issue B", "issue C"],
        }
        result = enforce_adversarial_mandate("pass", report)
        assert result == "pass"

    def test_pass_with_5_candidates_stays_pass(self):
        """pass + 5 failure_candidates → pass (exceeds minimum)."""
        report = {
            "validation_result": "pass",
            "failure_candidates": ["a", "b", "c", "d", "e"],
        }
        result = enforce_adversarial_mandate("pass", report)
        assert result == "pass"

    def test_pass_with_0_candidates_becomes_fail(self):
        """pass + 0 failure_candidates → fail (override)."""
        report = {"validation_result": "pass", "failure_candidates": []}
        result = enforce_adversarial_mandate("pass", report)
        assert result == "fail"

    def test_pass_with_2_candidates_becomes_fail(self):
        """pass + 2 failure_candidates → fail (below minimum 3)."""
        report = {
            "validation_result": "pass",
            "failure_candidates": ["issue A", "issue B"],
        }
        result = enforce_adversarial_mandate("pass", report)
        assert result == "fail"

    def test_pass_with_missing_field_becomes_fail(self):
        """pass + no failure_candidates field → fail (missing = 0)."""
        report = {"validation_result": "pass"}
        result = enforce_adversarial_mandate("pass", report)
        assert result == "fail"

    def test_pass_with_none_field_becomes_fail(self):
        """pass + failure_candidates=None → fail (None treated as empty)."""
        report = {"validation_result": "pass", "failure_candidates": None}
        result = enforce_adversarial_mandate("pass", report)
        assert result == "fail"

    def test_pass_with_non_list_field_becomes_fail(self):
        """pass + failure_candidates as string → fail (wrong type)."""
        report = {"validation_result": "pass", "failure_candidates": "some text"}
        result = enforce_adversarial_mandate("pass", report)
        assert result == "fail"

    def test_fail_verdict_not_affected(self):
        """fail verdict is never modified regardless of candidates."""
        report = {"validation_result": "fail", "failure_candidates": []}
        result = enforce_adversarial_mandate("fail", report)
        assert result == "fail"

    def test_warning_verdict_not_affected(self):
        """warning verdict is never modified regardless of candidates."""
        report = {"validation_result": "warning", "failure_candidates": []}
        result = enforce_adversarial_mandate("warning", report)
        assert result == "warning"

    def test_none_report_dict_not_affected(self):
        """pass + None report_dict → pass (can't check, no override)."""
        result = enforce_adversarial_mandate("pass", None)
        assert result == "pass"
