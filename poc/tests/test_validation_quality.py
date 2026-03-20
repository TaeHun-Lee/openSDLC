"""
Validation quality tests.

Verify that the artifact parser correctly identifies pass/fail/warning
and that obviously defective artifacts would trigger a fail verdict.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from artifacts.parser import (
    extract_yaml_from_response,
    parse_artifact,
    get_validation_result,
    artifact_to_yaml_str,
)


def test_extract_bare_yaml():
    raw = "artifact_id: UC-01\nvalidation_result: fail\n"
    result = extract_yaml_from_response(raw)
    assert "artifact_id" in result


def test_extract_fenced_yaml():
    raw = "Here is the report:\n```yaml\nartifact_id: UC-01-VAL-01\nvalidation_result: pass\n```"
    result = extract_yaml_from_response(raw)
    assert "artifact_id" in result
    assert "```" not in result


def test_parse_artifact_pass():
    yaml_str = "artifact_id: UC-01-VAL-01\nvalidation_result: pass\n"
    data = parse_artifact(yaml_str)
    assert data["artifact_id"] == "UC-01-VAL-01"
    assert get_validation_result(data) == "pass"


def test_parse_artifact_fail():
    yaml_str = "artifact_id: UC-01-VAL-01\nvalidation_result: fail\n"
    data = parse_artifact(yaml_str)
    assert get_validation_result(data) == "fail"


def test_parse_artifact_warning():
    yaml_str = "artifact_id: UC-01-VAL-01\nvalidation_result: warning\n"
    data = parse_artifact(yaml_str)
    assert get_validation_result(data) == "warning"


def test_unknown_result_defaults_to_fail():
    yaml_str = "artifact_id: UC-01-VAL-01\nvalidation_result: unknown_value\n"
    data = parse_artifact(yaml_str)
    assert get_validation_result(data) == "fail"


def test_missing_result_defaults_to_fail():
    yaml_str = "artifact_id: UC-01-VAL-01\n"
    data = parse_artifact(yaml_str)
    assert get_validation_result(data) == "fail"


def test_artifact_roundtrip():
    original = {"artifact_id": "UC-01", "validation_result": "pass"}
    yaml_str = artifact_to_yaml_str(original)
    restored = parse_artifact(yaml_str)
    assert restored["artifact_id"] == "UC-01"
    assert restored["validation_result"] == "pass"


if __name__ == "__main__":
    test_extract_bare_yaml()
    test_extract_fenced_yaml()
    test_parse_artifact_pass()
    test_parse_artifact_fail()
    test_parse_artifact_warning()
    test_unknown_result_defaults_to_fail()
    test_missing_result_defaults_to_fail()
    test_artifact_roundtrip()
    print("All validation quality tests passed.")
