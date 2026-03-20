# GEMINI.md - OpenSDLC v1 구현 가이드

이 문서는 Gemini CLI가 이 프로젝트에서 작업할 때 준수해야 할 핵심 지침을 담고 있다. OpenSDLC 방법론을 코드로 구현하는 과정에서 일관성과 품질을 유지하기 위해 이 규칙을 엄격히 따른다.

## 1. 프로젝트 개요
OpenSDLC는 AI 에이전트들이 구조화된 YAML 아티팩트를 통해 협업하는 소프트웨어 공장 플랫폼이다. 현재 목표는 LangGraph를 이용해 에이전트 간 컨텍스트를 완전히 격리한 PoC(Proof of Concept)를 구현하는 것이다.

## 2. 프로젝트 빌드 및 실행
프로젝트는 `poc/` 디렉토리 내에 구현된다.

- **의존성 설치**: `cd poc && pip install -e .` (또는 `poetry install`)
- **환경 변수 설정**: `.env` 파일에 `ANTHROPIC_API_KEY` 설정 필수
- **PoC 실행**: `python poc/run_poc.py`
- **서버 실행**: `uvicorn poc.src.api:app --reload` (FastAPI 구현 시)

## 3. 테스트 명령어
에이전트의 독립성과 검증 품질을 확인하기 위한 테스트를 수행한다.

- **전체 테스트 실행**: `pytest poc/tests/`
- **컨텍스트 격리 테스트**: `pytest poc/tests/test_context_isolation.py`
- **검증 품질 테스트**: `pytest poc/tests/test_validation_quality.py`

## 4. 코딩 스타일 및 기술 제약
- **언어 및 런타임**: Python 3.11 이상 사용
- **타입 시스템**: 모든 함수와 클래스에 Python Type Hints 필수 적용
- **비동기 프로그래밍**: 모든 LLM API 호출 및 입출력 작업은 `async/await` 사용
- **데이터 검증**: YAML 아티팩트 파싱 및 스키마 검증에는 `pydantic` 및 `pyyaml` 사용
- **상태 관리**: LangGraph의 `StateGraph`를 사용하여 에이전트 워크플로우 정의
- **에이전트 노드**: 각 노드는 부수 효과가 없는 순수 함수로 구현 (State In -> State Out)

## 5. 핵심 설계 원칙: 컨텍스트 격리
에이전트 간의 '자기 채점' 문제를 방지하기 위해 다음 원칙을 반드시 준수한다.

- **독립 호출**: 각 에이전트는 별도의 LLM API 호출로 실행되어야 함
- **데이터 최소 전달**: 에이전트 간에는 오직 YAML 아티팩트 문자열만 전달하며, 이전 에이전트의 사고 과정(Chain of Thought)이나 시스템 프롬프트는 절대 공유하지 않음
- **역할 정의**: `open-sdlc-engine/prompts/agent/`에 정의된 프롬프트를 읽기 전용으로 참조하여 사용

## 6. 아티팩트 및 프롬프트 참조
구현 시 다음 경로의 파일들을 표준으로 삼는다.

- **에이전트 규칙**: `open-sdlc-engine/core-concepts/agent-definitions.md`
- **워크플로우**: `open-sdlc-engine/core-concepts/workflow.md`
- **아티팩트 템플릿**: `open-sdlc-engine/templates/artifacts/`
- **시스템 프롬프트**: `open-sdlc-engine/prompts/`
- **최상위 규범**: `open-sdlc-constitution/`

## 7. 검증 에이전트(Validator) 강화 규칙
검증 에이전트는 결함을 찾아내는 데 공격적이어야 한다.
- **Adversarial Prompting**: 통과(pass) 판정 전 반드시 실패 사유 후보를 3개 이상 도출하도록 강제함
- **체크리스트 준수**: 스키마, 추적성, 근거, 논리적 일관성, 역할 경계, 회귀 방지의 6가지 기준을 엄격히 적용함
