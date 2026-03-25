"""Tests for PMAgent decision extraction robustness (improvement ①)."""

import pytest

from app.core.executor.generic_agent import (
    _extract_pm_decision,
    _extract_satisfaction_score,
    _strip_markdown_noise,
)


class TestStripMarkdownNoise:
    def test_strips_code_fences(self):
        text = "```yaml\nITERATION_DECISION: done\n```"
        assert "```" not in _strip_markdown_noise(text)

    def test_strips_bold_and_backticks(self):
        text = "**ITERATION_DECISION**: `continue`"
        cleaned = _strip_markdown_noise(text)
        assert "*" not in cleaned
        assert "`" not in cleaned


class TestExtractPmDecision:
    """Test _extract_pm_decision against common LLM formatting variations."""

    def test_standard_format(self):
        assert _extract_pm_decision("ITERATION_DECISION: continue") == "continue"
        assert _extract_pm_decision("ITERATION_DECISION: done") == "done"

    def test_case_insensitive(self):
        assert _extract_pm_decision("iteration_decision: CONTINUE") == "continue"
        assert _extract_pm_decision("Iteration_Decision: Done") == "done"

    def test_equals_separator(self):
        assert _extract_pm_decision("ITERATION_DECISION = continue") == "continue"

    def test_dash_separator(self):
        assert _extract_pm_decision("ITERATION_DECISION - done") == "done"

    def test_extra_whitespace(self):
        assert _extract_pm_decision("ITERATION_DECISION:   continue") == "continue"
        assert _extract_pm_decision("ITERATION_DECISION :continue") == "continue"

    def test_quoted_values(self):
        assert _extract_pm_decision('ITERATION_DECISION: "continue"') == "continue"
        assert _extract_pm_decision("ITERATION_DECISION: 'done'") == "done"

    def test_markdown_code_block(self):
        text = "분석 결과:\n```yaml\nITERATION_DECISION: continue\nSATISFACTION_SCORE: 75\n```"
        assert _extract_pm_decision(text) == "continue"

    def test_markdown_bold_wrapping(self):
        text = "**ITERATION_DECISION**: **continue**"
        assert _extract_pm_decision(text) == "continue"

    def test_backtick_wrapping(self):
        text = "`ITERATION_DECISION`: `done`"
        assert _extract_pm_decision(text) == "done"

    def test_space_instead_of_underscore(self):
        assert _extract_pm_decision("ITERATION DECISION: continue") == "continue"

    def test_hyphen_instead_of_underscore(self):
        assert _extract_pm_decision("ITERATION-DECISION: done") == "done"

    def test_embedded_in_long_text(self):
        text = (
            "[PMAgent] 이번 iteration에서는 요구사항이 잘 반영되었습니다.\n"
            "ITERATION_DECISION: done\n"
            "SATISFACTION_SCORE: 90\n"
            "다음 작업은 불필요합니다."
        )
        assert _extract_pm_decision(text) == "done"

    def test_not_found_defaults_to_continue(self):
        assert _extract_pm_decision("no decision here") == "continue"


class TestExtractSatisfactionScore:
    """Test _extract_satisfaction_score against formatting variations."""

    def test_standard_format(self):
        assert _extract_satisfaction_score("SATISFACTION_SCORE: 85") == 85

    def test_equals_separator(self):
        assert _extract_satisfaction_score("SATISFACTION_SCORE = 90") == 90

    def test_quoted_value(self):
        assert _extract_satisfaction_score('SATISFACTION_SCORE: "75"') == 75

    def test_markdown_code_block(self):
        text = "```\nSATISFACTION_SCORE: 60\n```"
        assert _extract_satisfaction_score(text) == 60

    def test_space_instead_of_underscore(self):
        assert _extract_satisfaction_score("SATISFACTION SCORE: 70") == 70

    def test_not_found_defaults_to_zero(self):
        assert _extract_satisfaction_score("no score") == 0
