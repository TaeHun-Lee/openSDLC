import pytest
import re
from app.core.artifacts.parser import (
    extract_code_blocks_from_narrative,
    split_narrative_and_yaml,
    strip_code_blocks_from_narrative,
)
from app.core.llm_client import _extract_google_text
from app.core.pipeline.routing import make_validator_router

def test_strip_code_blocks():
    """Fix 1-A: narrative에서 bare 코드 블럭 및 잘린 코드 블럭 제거 테스트"""
    narrative = (
        "Here is some text.\n"
        "<!-- FILE: src/app.py -->\n"
        "```python\nprint('hello')\n```\n"
        "Middle text.\n"
        "```html\n<div>Bare block</div>\n```\n"
        "Ending text.\n"
        "```tsx\nimport React from 'react';\n// Truncated block without closing fence"
    )
    
    stripped = strip_code_blocks_from_narrative(narrative)
    
    # 1. FILE 마커 블럭 제거 확인
    assert "src/app.py" not in stripped
    assert "print('hello')" not in stripped
    
    # 2. Bare 블럭 제거 확인
    assert "<div>Bare block</div>" not in stripped
    assert "```html" not in stripped
    
    # 3. 잘린 블럭 제거 확인
    assert "import React" not in stripped
    assert "Truncated block" not in stripped
    
    # 4. 일반 텍스트 보존 확인
    assert "Here is some text." in stripped
    assert "Middle text." in stripped
    assert "Ending text." in stripped

def test_extract_truncated_code_blocks():
    """Fix 1-B: 잘린 FILE 마커 코드 블럭 추출 테스트"""
    narrative = (
        "Introduction.\n"
        "<!-- FILE: src/complete.py -->\n"
        "```python\nprint('complete')\n```\n"
        "Between blocks.\n"
        "<!-- FILE: src/truncated.py -->\n"
        "```python\nprint('truncated content')\n# No closing fence here"
    )
    
    results = extract_code_blocks_from_narrative(narrative)
    
    assert len(results) == 2
    
    # 1. 완전한 블럭 확인
    assert results[0]["path"] == "src/complete.py"
    assert results[0]["content"] == "print('complete')"
    
    # 2. 잘린 블럭 확인
    assert results[1]["path"] == "src/truncated.py"
    assert "print('truncated content')" in results[1]["content"]
    assert "# No closing fence here" in results[1]["content"]

def test_extract_google_text_none_defense():
    """Fix 2-A: Google API 응답 None 텍스트 방어 테스트"""
    class MockResponse:
        def __init__(self, text, candidates=None):
            self.text = text
            self.candidates = candidates or []
            
    # Case 1: 정상 텍스트
    resp_ok = MockResponse("Normal response")
    assert _extract_google_text(resp_ok, "gemini-pro") == "Normal response"
    
    # Case 2: None 텍스트
    resp_none = MockResponse(None)
    assert _extract_google_text(resp_none, "gemini-pro") == ""


def test_split_narrative_and_yaml_extracts_yaml_without_artifact_id():
    """Phase 2: artifact_id 없는 fenced YAML dict도 분리되어야 한다."""
    response_text = (
        "[PMAgent] Assessment follows.\n"
        "```yaml\n"
        "decision: continue\n"
        "score: 78\n"
        "```\n"
        "[PMAgent] End."
    )

    narrative, artifact_yaml = split_narrative_and_yaml(response_text)

    assert "Assessment follows" in narrative
    assert "End." in narrative
    assert "decision: continue" in artifact_yaml
    assert "score: 78" in artifact_yaml


def test_validator_router_uses_gate_local_rework_counts():
    """Phase 1: gate별 rework count만 참조해야 한다."""
    router = make_validator_router(step_num=7)
    state = {
        "steps_completed": [{"validation_result": "fail"}],
        "rework_counts": {5: 3, 7: 1},
        "max_reworks_per_gate": 3,
    }

    assert router(state) == "rework"


def test_validator_router_routes_warning_to_warning_branch():
    """Phase 2: warning은 rework가 아니라 warning branch로 가야 한다."""
    router = make_validator_router(step_num=7)
    state = {
        "steps_completed": [{"validation_result": "warning"}],
        "rework_counts": {7: 0},
        "max_reworks_per_gate": 3,
    }

    assert router(state) == "warning"
