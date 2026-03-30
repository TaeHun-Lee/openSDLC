"""Tests for ValidatorAgent adversarial mandate check.

The mandate now logs warnings but does NOT override pass verdicts.
All pass results remain pass regardless of failure_candidates count.
"""

import pytest

from app.core.executor.generic_agent import enforce_adversarial_mandate


class TestEnforceAdversarialMandate:
    """Test enforce_adversarial_mandate function directly."""

    def test_pass_with_3_candidates_stays_pass(self):
        """pass + 3 failure_candidates → pass (mandate satisfied)."""
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

    def test_pass_with_0_candidates_stays_pass(self):
        """pass + 0 failure_candidates → pass (warning only, no override)."""
        report = {"validation_result": "pass", "failure_candidates": []}
        result = enforce_adversarial_mandate("pass", report)
        assert result == "pass"

    def test_pass_with_2_candidates_stays_pass(self):
        """pass + 2 failure_candidates → pass (warning only, no override)."""
        report = {
            "validation_result": "pass",
            "failure_candidates": ["issue A", "issue B"],
        }
        result = enforce_adversarial_mandate("pass", report)
        assert result == "pass"

    def test_pass_with_missing_field_stays_pass(self):
        """pass + no failure_candidates field → pass (warning only)."""
        report = {"validation_result": "pass"}
        result = enforce_adversarial_mandate("pass", report)
        assert result == "pass"

    def test_pass_with_none_field_stays_pass(self):
        """pass + failure_candidates=None → pass (warning only)."""
        report = {"validation_result": "pass", "failure_candidates": None}
        result = enforce_adversarial_mandate("pass", report)
        assert result == "pass"

    def test_pass_with_non_list_field_stays_pass(self):
        """pass + failure_candidates as string → pass (warning only)."""
        report = {"validation_result": "pass", "failure_candidates": "some text"}
        result = enforce_adversarial_mandate("pass", report)
        assert result == "pass"

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
