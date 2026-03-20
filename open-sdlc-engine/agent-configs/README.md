# OpenSDLC Agent Configurations

이 폴더는 OpenSDLC v1에서 사용하는 각 Agent를 독립적으로 구성하기 위한 런타임 설정 레이어입니다.

목적:
- Agent별 역할, 입출력 계약, 핸드오프 경로를 분리 관리
- 공통 규칙과 개별 역할 프롬프트를 조합할 수 있는 기준 제공
- Agent마다 일관된 페르소나를 부여하여 출력 품질과 톤을 안정화

구성 원칙:
- 공통 규칙은 `open-sdlc-engine/prompts/agent/AgentCommon.txt`를 우선 적용
- 역할별 세부 규칙은 각 Agent의 개별 프롬프트 파일을 적용
- 본 폴더의 설정 파일은 프롬프트를 대체하지 않고, 독립 실행을 위한 구성 정보와 페르소나를 제공
- 실제 산출물 생성 시에는 반드시 해당 아티팩트 템플릿을 먼저 읽고 스키마를 준수
- 사용자 입력/승인 질의는 `PMAgent`만 담당하며, 진행 보고는 현재 활성 Agent가 자신의 1인칭 시점으로 직접 수행
- 다음 이터레이션 피드백은 `CoordAgent -> PMAgent -> ReqAgent` 경로로 전달되며, `CodeAgent`는 피드백을 직접 입력으로 소비하지 않음

권장 조합 순서:
1. `AgentCommon.txt`
2. 역할별 프롬프트 (`PMAgent.txt`, `ReqAgent.txt` 등)
3. 본 폴더의 Agent 설정 파일

포함 파일:
- `PMAgent.config.yaml`
- `ReqAgent.config.yaml`
- `ValidatorAgent.config.yaml`
- `CodeAgent.config.yaml`
- `TestAgent.config.yaml`
- `CoordAgent.config.yaml`
