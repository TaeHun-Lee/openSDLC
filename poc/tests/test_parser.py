"""Tests for artifacts.parser — especially indentation recovery."""

import pytest

from src.artifacts.parser import (
    _normalize_yaml_indentation,
    parse_artifact,
    extract_yaml_from_response,
    split_narrative_and_yaml,
)


class TestNormalizeYamlIndentation:
    """Test _normalize_yaml_indentation helper."""

    def test_fixes_first_line_no_indent_rest_indented(self):
        """The exact bug pattern from the issue: first line at col 0, rest at col 2."""
        bad_yaml = (
            'artifact_id: "TD-01-VAL-1"\n'
            '  artifact_type: "ValidationReportArtifact"\n'
            '  iteration: 1\n'
            '  created_by: "ValidatorAgent"'
        )
        fixed = _normalize_yaml_indentation(bad_yaml)
        assert fixed == (
            'artifact_id: "TD-01-VAL-1"\n'
            'artifact_type: "ValidationReportArtifact"\n'
            'iteration: 1\n'
            'created_by: "ValidatorAgent"'
        )

    def test_already_correct_indentation(self):
        """Properly formatted YAML should be returned unchanged."""
        good_yaml = (
            'artifact_id: "X"\n'
            'artifact_type: "Y"\n'
            'iteration: 1'
        )
        assert _normalize_yaml_indentation(good_yaml) == good_yaml

    def test_preserves_nested_indentation(self):
        """Nested structures should keep their relative indentation."""
        bad_yaml = (
            'artifact_id: "X"\n'
            '  items:\n'
            '    - name: "a"\n'
            '    - name: "b"'
        )
        fixed = _normalize_yaml_indentation(bad_yaml)
        assert fixed == (
            'artifact_id: "X"\n'
            'items:\n'
            '  - name: "a"\n'
            '  - name: "b"'
        )

    def test_blank_lines_preserved(self):
        """Blank lines should not cause issues."""
        bad_yaml = (
            'artifact_id: "X"\n'
            '  artifact_type: "Y"\n'
            '\n'
            '  iteration: 1'
        )
        fixed = _normalize_yaml_indentation(bad_yaml)
        assert fixed == (
            'artifact_id: "X"\n'
            'artifact_type: "Y"\n'
            '\n'
            'iteration: 1'
        )

    def test_single_line_unchanged(self):
        assert _normalize_yaml_indentation('artifact_id: "X"') == 'artifact_id: "X"'


class TestParseArtifactIndentRecovery:
    """Test that parse_artifact recovers from the indentation bug."""

    def test_parses_misindented_yaml(self):
        bad_yaml = (
            'artifact_id: "TD-01-VAL-1"\n'
            '  artifact_type: "ValidationReportArtifact"\n'
            '  iteration: 1\n'
            '  validation_result: "pass"'
        )
        result = parse_artifact(bad_yaml)
        assert result["artifact_id"] == "TD-01-VAL-1"
        assert result["artifact_type"] == "ValidationReportArtifact"
        assert result["iteration"] == 1
        assert result["validation_result"] == "pass"

    def test_parses_misindented_yaml_in_code_fence(self):
        response = (
            "Here is the validation report:\n"
            "```yaml\n"
            'artifact_id: "TD-01-VAL-1"\n'
            '  artifact_type: "ValidationReportArtifact"\n'
            '  validation_result: "fail"\n'
            "```"
        )
        result = parse_artifact(response)
        assert result["artifact_id"] == "TD-01-VAL-1"
        assert result["validation_result"] == "fail"
