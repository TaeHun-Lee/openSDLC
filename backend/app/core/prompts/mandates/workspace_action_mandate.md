# Workspace Action Mandate

PMAgent는 프로젝트 초기화(Step 1: Initializer) 시 제공된 작업 공간(Workspace) 파일 목록을 분석하여 실행 전략을 결정해야 한다.

## 1. PM_ACTION_TYPE 결정
PMAgent는 User Story와 현재 작업 공간 상태를 비교하여 다음 중 하나를 결정한다:
- **new**: 작업 공간이 비어 있거나, User Story가 기존 코드와 무관한 새로운 프로젝트를 생성하는 경우.
- **modify**: User Story가 기존 작업 공간에 있는 파일을 수정, 기능 추가, 또는 변경하는 경우.

PMAgent는 Initializer 응답 마지막에 반드시 아래 형식의 판정 블록을 포함해야 한다:
```
PM_ACTION_TYPE: new (또는 modify)
```

## 2. 작업 공간 인식 (Workspace Awareness)
PMAgent는 작업 공간에 있는 파일 목록을 ReqAgent에게 전달할 때 'modify' 모드임을 명시하고, 기존 구조를 존중하여 요구사항(Use Case)을 설계하도록 지시해야 한다.
ReqAgent는 기존 파일 목록을 참고하여 신규 기능이 기존 시스템과 어떻게 통합될지 정의해야 한다.
CodeAgent는 기존 파일 내용을 직접 읽고 필요한 부분만 수정하거나 추가해야 한다.
