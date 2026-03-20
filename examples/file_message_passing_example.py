"""
OpenSDLC - File-Based Message Passing 구현 예시
================================================
Agent 간 통신을 파일 시스템으로 수행하는 패턴의 전체 구현 예시입니다.

핵심 개념:
- 각 Agent는 정해진 디렉토리에 .md 파일을 "쓰기"로 산출물 생성
- CoodAgent(오케스트레이터)가 해당 파일을 "읽어서" 다음 Agent에게 전달
- 모든 산출물은 디스크에 영속화되어 이력 추적, 사용자 검토, 다음 iteration 참조 가능
"""

import os
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# ============================================================
# 1. 프로젝트 디렉토리 구조 정의
# ============================================================

class ProjectStructure:
    """
    프로젝트의 파일 시스템 구조를 관리합니다.
    이 구조 자체가 Agent 간 메시지 패싱의 "채널"이 됩니다.
    
    실제 디렉토리 구조:
    
    projects/my-todo-app/
    ├── project.json                    # 프로젝트 메타정보
    ├── iterations/
    │   └── iter-1/
    │       ├── goals.md                # 이번 iteration 목표
    │       ├── req-agent/
    │       │   ├── output.md           # 산출물 (사람용 요약)
    │       │   ├── prompt-to-logi.md   # LogiAgent에게 보낼 작업지시서 ← 이것이 "메시지"
    │       │   ├── prompt-to-phys.md   # PhysAgent에게 보낼 품질/제약사항
    │       │   └── log.md              # plan-do-see-feedback 이력
    │       ├── logi-agent/
    │       │   ├── output.md
    │       │   ├── prompt-to-phys.md   # PhysAgent에게 보낼 작업지시서
    │       │   └── log.md
    │       ├── phys-agent/
    │       │   ├── output.md
    │       │   ├── prompt-to-cons.md   # ConsAgent에게 보낼 작업지시서
    │       │   └── log.md
    │       ├── cons-agent/
    │       │   ├── output.md
    │       │   └── log.md
    │       └── feedback/
    │           ├── evaluation.md
    │           └── user-review.md
    └── workspace/                      # 실제 코드 작업 공간
    """
    
    def __init__(self, base_dir: str, project_name: str):
        self.base = Path(base_dir) / project_name
    
    def agent_dir(self, iteration: int, agent_name: str) -> Path:
        """특정 iteration의 특정 Agent 작업 디렉토리"""
        return self.base / "iterations" / f"iter-{iteration}" / agent_name
    
    def output_path(self, iteration: int, agent_name: str) -> Path:
        """Agent의 산출물 파일 경로"""
        return self.agent_dir(iteration, agent_name) / "output.md"
    
    def prompt_path(self, iteration: int, from_agent: str, to_agent: str) -> Path:
        """Agent A가 Agent B에게 보낼 작업지시서 파일 경로 (= 메시지)"""
        return self.agent_dir(iteration, from_agent) / f"prompt-to-{to_agent}.md"
    
    def log_path(self, iteration: int, agent_name: str) -> Path:
        """Agent의 작업 이력 파일"""
        return self.agent_dir(iteration, agent_name) / "log.md"
    
    def init_iteration(self, iteration: int):
        """새 iteration에 필요한 디렉토리 구조 생성"""
        agents = ["req-agent", "logi-agent", "phys-agent", "cons-agent", "feedback"]
        for agent in agents:
            (self.agent_dir(iteration, agent)).mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. 메시지(작업지시서) 포맷 정의
# ============================================================

@dataclass
class WorkOrder:
    """
    Agent 간 전달되는 작업지시서 = 파일 기반 메시지의 본체
    
    이 객체가 .md 파일로 직렬화되어 디스크에 저장됩니다.
    다음 Agent는 이 파일을 읽어서 WorkOrder로 역직렬화합니다.
    """
    from_agent: str               # 발신 Agent
    to_agent: str                 # 수신 Agent
    iteration: int                # 현재 iteration 번호
    timestamp: str = ""           # 생성 시각
    
    # 핵심 페이로드
    task_description: str = ""    # 수행할 작업 설명
    context: str = ""             # 이전 단계 산출물 요약 (context window 절약용)
    full_artifacts: list = field(default_factory=list)  # 참조할 전체 산출물 파일 경로들
    constraints: list = field(default_factory=list)      # 제약사항
    
    # 메타
    status: str = "pending"       # pending → in_progress → completed → reviewed
    
    def to_markdown(self) -> str:
        """
        작업지시서를 마크다운 파일로 직렬화.
        이 파일이 곧 LLM 프롬프트의 재료가 됩니다.
        """
        md = f"""# Work order: {self.from_agent} → {self.to_agent}

- **Iteration**: {self.iteration}
- **Created**: {self.timestamp}
- **Status**: {self.status}

## Task

{self.task_description}

## Context from previous step

{self.context}

## Referenced artifacts

{chr(10).join(f'- `{a}`' for a in self.full_artifacts) if self.full_artifacts else '(none)'}

## Constraints

{chr(10).join(f'- {c}' for c in self.constraints) if self.constraints else '(none)'}
"""
        return md
    
    @classmethod
    def from_markdown(cls, md_text: str, filepath: str = "") -> 'WorkOrder':
        """
        마크다운 파일에서 작업지시서를 역직렬화.
        단순 파싱이므로 LLM이 생성한 자유 형식 마크다운도 처리 가능.
        """
        # 실제 구현에서는 정규식이나 마크다운 파서로 각 섹션을 추출
        # 여기서는 개념 시연용으로 간략화
        return cls(
            from_agent="parsed",
            to_agent="parsed", 
            iteration=0,
            task_description=md_text,
        )


# ============================================================
# 3. Agent 기본 클래스 - 파일 읽기/쓰기 패턴
# ============================================================

class BaseAgent:
    """
    모든 Agent의 기본 클래스.
    핵심: read_input() → process() → write_output()
    
    파일 기반 메시지 패싱에서 Agent가 하는 일은 결국:
    1. 지정된 경로에서 작업지시서(.md) 파일을 읽고
    2. LLM을 호출하여 작업을 수행하고
    3. 결과를 지정된 경로에 .md 파일로 쓰는 것
    """
    
    def __init__(self, name: str, project: ProjectStructure):
        self.name = name
        self.project = project
    
    def read_input(self, iteration: int, from_agent: str) -> str:
        """
        이전 Agent가 남긴 작업지시서(메시지) 파일을 읽습니다.
        파일이 없으면 아직 이전 단계가 완료되지 않은 것입니다.
        """
        prompt_file = self.project.prompt_path(iteration, from_agent, self.name)
        
        if not prompt_file.exists():
            raise FileNotFoundError(
                f"Work order not found: {prompt_file}\n"
                f"{from_agent} has not completed its work yet."
            )
        
        content = prompt_file.read_text(encoding="utf-8")
        
        # 이전 iteration의 이력도 함께 로드 (Spiral model의 핵심)
        prev_context = self._load_previous_iteration_context(iteration)
        
        return content + "\n\n" + prev_context if prev_context else content
    
    def write_output(self, iteration: int, output_content: str, 
                     next_agents: dict[str, str] = None):
        """
        작업 결과를 파일로 씁니다.
        
        두 종류의 파일을 생성:
        1. output.md: 사람이 검토할 수 있는 산출물 요약
        2. prompt-to-{next}.md: 다음 Agent에게 보낼 작업지시서 (= 메시지)
        """
        agent_dir = self.project.agent_dir(iteration, self.name)
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # 1) 산출물 저장 (사람용)
        output_path = self.project.output_path(iteration, self.name)
        output_path.write_text(output_content, encoding="utf-8")
        print(f"  [WRITE] {output_path}")
        
        # 2) 다음 Agent별 작업지시서 생성 (= 메시지 발송)
        if next_agents:
            for next_agent_name, task_for_next in next_agents.items():
                work_order = WorkOrder(
                    from_agent=self.name,
                    to_agent=next_agent_name,
                    iteration=iteration,
                    timestamp=datetime.now().isoformat(),
                    task_description=task_for_next,
                    context=self._summarize(output_content),  # 요약본 전달
                    full_artifacts=[str(output_path)],         # 전체본 경로 참조
                )
                
                prompt_file = self.project.prompt_path(
                    iteration, self.name, next_agent_name
                )
                prompt_file.write_text(
                    work_order.to_markdown(), encoding="utf-8"
                )
                print(f"  [MSG →] {self.name} → {next_agent_name}: {prompt_file}")
    
    def write_log(self, iteration: int, plan: str, result: str, 
                  reflection: str, feedback: str):
        """
        plan-do-see-self feedback 기반 작업 이력을 기록합니다.
        이 로그 파일이 Agent의 "기억"이 됩니다.
        """
        log_path = self.project.log_path(iteration, self.name)
        
        log_entry = f"""## Iteration {iteration} - {datetime.now().isoformat()}

### Plan
{plan}

### Do (result)
{result}

### See (observation)
{reflection}

### Self-feedback
{feedback}

---

"""
        # 기존 로그에 append
        mode = "a" if log_path.exists() else "w"
        with open(log_path, mode, encoding="utf-8") as f:
            f.write(log_entry)
        
        print(f"  [LOG] {log_path}")
    
    def _load_previous_iteration_context(self, current_iter: int) -> str:
        """이전 iteration의 산출물을 context로 로드 (Spiral 반복의 핵심)"""
        if current_iter <= 1:
            return ""
        
        prev_output = self.project.output_path(current_iter - 1, self.name)
        if prev_output.exists():
            content = prev_output.read_text(encoding="utf-8")
            return f"\n## Previous iteration ({current_iter - 1}) output\n\n{content}"
        return ""
    
    def _summarize(self, content: str, max_chars: int = 2000) -> str:
        """
        산출물 요약 (context window 절약용).
        실제로는 LLM을 호출하여 요약하거나, 핵심 섹션만 추출합니다.
        """
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "\n\n... (truncated, see full artifact)"


# ============================================================
# 4. 구체적 Agent 구현 예시
# ============================================================

class RequAgent(BaseAgent):
    """
    요구사항 수집 및 정제 Agent.
    
    입력: 사용자의 원본 요청 (또는 이전 iteration의 피드백)
    출력: 
      - output.md: 정제된 요구사항 문서
      - prompt-to-logi.md: LogiAgent에게 보낼 기능 요구사항 작업지시서
      - prompt-to-phys.md: PhysAgent에게 보낼 품질/제약사항 작업지시서
    """
    
    def __init__(self, project: ProjectStructure, llm_client=None):
        super().__init__("req-agent", project)
        self.llm = llm_client  # Anthropic Claude API client
    
    def run(self, iteration: int, user_request: str) -> str:
        """
        RequAgent의 전체 실행 흐름.
        """
        print(f"\n{'='*50}")
        print(f"[RequAgent] Starting iteration {iteration}")
        print(f"{'='*50}")
        
        # --- PLAN ---
        plan = f"Analyze user request and produce requirement specification"
        
        # --- DO: LLM 호출하여 요구사항 분석 ---
        system_prompt = self._build_system_prompt(iteration)
        
        # 이전 iteration 피드백이 있으면 반영
        prev_feedback = self._load_feedback(iteration)
        
        full_prompt = f"""
{system_prompt}

## User request
{user_request}

{prev_feedback}

Please analyze this request and produce:
1. Functional requirements with use cases
2. Quality requirements  
3. Constraints
4. Test scenarios
"""
        
        # 실제로는 여기서 LLM API 호출
        # response = self.llm.messages.create(model="claude-sonnet-4-20250514", ...)
        # 시연용으로 mock response 사용
        llm_response = self._mock_llm_response(user_request)
        
        # --- WRITE OUTPUT: 산출물 + 메시지(작업지시서) 생성 ---
        self.write_output(
            iteration=iteration,
            output_content=llm_response["full_output"],
            next_agents={
                # LogiAgent에게 보낼 메시지: 기능 요구사항
                "logi-agent": llm_response["functional_requirements"],
                # PhysAgent에게 보낼 메시지: 품질/제약사항  
                "phys-agent": llm_response["quality_and_constraints"],
            }
        )
        
        # --- SEE + SELF-FEEDBACK: 이력 기록 ---
        self.write_log(
            iteration=iteration,
            plan=plan,
            result=f"Generated {len(llm_response['full_output'])} chars of requirements",
            reflection="Requirements cover all aspects of user request",
            feedback="Next iteration should refine edge cases in UC-002",
        )
        
        print(f"[RequAgent] Completed iteration {iteration}")
        return llm_response["full_output"]
    
    def _build_system_prompt(self, iteration: int) -> str:
        return """You are RequAgent, a requirements analysis specialist.
Your role is to transform user requests into structured requirement documents.

Output format:
- Functional requirements as use cases (UC-001, UC-002, ...)
- Each use case includes: actor, trigger, main flow, alternative flows
- Quality requirements (performance, security, usability)
- Constraints (technical stack, deployment environment)
- Test scenarios for each use case"""
    
    def _load_feedback(self, iteration: int) -> str:
        """이전 iteration의 피드백을 로드하여 이번 작업에 반영"""
        if iteration <= 1:
            return ""
        feedback_path = (self.project.base / "iterations" / 
                        f"iter-{iteration-1}" / "feedback" / "user-review.md")
        if feedback_path.exists():
            content = feedback_path.read_text(encoding="utf-8")
            return f"\n## Feedback from previous iteration\n\n{content}"
        return ""
    
    def _mock_llm_response(self, user_request: str) -> dict:
        """시연용 mock - 실제로는 Claude API 호출"""
        return {
            "full_output": f"""# Requirements Specification

## Project overview
{user_request}

## Functional requirements

### UC-001: User registration
- **Actor**: New user
- **Trigger**: User clicks "Sign up"
- **Main flow**:
  1. System displays registration form
  2. User enters email and password
  3. System validates and creates account
- **Test scenario**: Valid email → account created, duplicate email → error shown

### UC-002: Task creation
- **Actor**: Authenticated user
- **Trigger**: User clicks "Add task"
- **Main flow**:
  1. System displays task form
  2. User enters title, description, due date
  3. System saves task and shows confirmation

## Quality requirements
- Response time < 200ms for API calls
- Support 1000 concurrent users
- WCAG 2.1 AA accessibility

## Constraints
- Frontend: React + TypeScript
- Backend: Python FastAPI
- Database: PostgreSQL
- Deployment: Docker containers
""",
            "functional_requirements": """Based on the requirements analysis, implement the following:

1. **UC-001 User Registration**: Design a registration workflow with email/password.
   - Screen: Registration form with validation
   - API: POST /api/auth/register
   - Data: users table with email, password_hash, created_at

2. **UC-002 Task Creation**: Design a task management workflow.
   - Screen: Task creation form with title, description, due_date
   - API: POST /api/tasks, GET /api/tasks
   - Data: tasks table with title, description, due_date, user_id, status

Please design the logical workflow, API structure, and entity model for these use cases.""",
            
            "quality_and_constraints": """Apply these quality requirements and constraints:

**Quality requirements:**
- API response time < 200ms
- Support 1000 concurrent users
- WCAG 2.1 AA accessibility compliance

**Technical constraints:**
- Frontend: React + TypeScript
- Backend: Python FastAPI  
- Database: PostgreSQL
- Deployment: Docker containers

Please factor these into your physical architecture design."""
        }


# ============================================================
# 5. 오케스트레이터 - 파일 기반 라우팅
# ============================================================

class CoodAgent:
    """
    오케스트레이션 Agent.
    
    핵심 역할: 파일 시스템을 감시하며 Agent 간 작업 흐름을 제어합니다.
    
    동작 방식:
    1. Agent A가 작업 완료 → output.md + prompt-to-B.md 파일 생성
    2. CoodAgent가 prompt-to-B.md 존재 확인 (= 메시지 수신 확인)
    3. prompt-to-B.md를 읽어서 검증 (빠진 정보 없는지, 포맷 올바른지)
    4. Agent B를 실행하며 해당 파일 경로를 전달
    """
    
    def __init__(self, project: ProjectStructure):
        self.project = project
        self.agents = {}  # name → agent instance
        
        # Agent 실행 순서 정의 (파이프라인)
        self.pipeline = [
            ("req-agent",  ["logi-agent", "phys-agent"]),  # req → logi, phys
            ("logi-agent", ["phys-agent"]),                 # logi → phys
            ("phys-agent", ["cons-agent"]),                 # phys → cons
            ("cons-agent", []),                             # cons → (test)
        ]
    
    def register_agent(self, name: str, agent: BaseAgent):
        self.agents[name] = agent
    
    def run_iteration(self, iteration: int, user_request: str = ""):
        """
        하나의 Spiral iteration을 실행합니다.
        
        이것이 파일 기반 메시지 패싱의 전체 흐름입니다:
        Agent 실행 → 파일 쓰기 → 파일 확인 → 다음 Agent 실행
        """
        print(f"\n{'#'*60}")
        print(f"# ITERATION {iteration} START")
        print(f"{'#'*60}")
        
        self.project.init_iteration(iteration)
        
        for agent_name, next_agents in self.pipeline:
            agent = self.agents.get(agent_name)
            if not agent:
                print(f"  [SKIP] {agent_name} not registered")
                continue
            
            # === 메시지(파일) 존재 확인 ===
            if agent_name == "req-agent":
                # 첫 Agent는 사용자 입력을 직접 받음
                agent.run(iteration, user_request)
            else:
                # 이전 Agent가 남긴 작업지시서(파일)가 있는지 확인
                ready = self._check_inputs_ready(iteration, agent_name)
                if not ready:
                    print(f"  [WAIT] {agent_name}: inputs not ready, skipping")
                    continue
                
                # 입력 파일들을 읽어서 Agent에게 전달
                combined_input = self._gather_inputs(iteration, agent_name)
                agent.run(iteration, combined_input)
            
            # === 산출물(파일) 검증 ===
            output_valid = self._validate_output(iteration, agent_name)
            if not output_valid:
                print(f"  [ERROR] {agent_name}: output validation failed")
                # 실패 시 재실행 또는 사용자에게 알림
                break
            
            # === 다음 Agent에게 보낼 메시지(파일) 존재 확인 ===
            for next_name in next_agents:
                msg_path = self.project.prompt_path(iteration, agent_name, next_name)
                if msg_path.exists():
                    print(f"  [ROUTE] Message ready: {agent_name} → {next_name}")
                else:
                    print(f"  [WARN] Expected message not found: {msg_path}")
        
        print(f"\n# ITERATION {iteration} COMPLETE")
        self._summarize_iteration(iteration)
    
    def _check_inputs_ready(self, iteration: int, agent_name: str) -> bool:
        """
        Agent에게 필요한 입력 파일(메시지)들이 모두 존재하는지 확인.
        파일 존재 여부 = 메시지 수신 여부
        """
        # 어떤 Agent들로부터 메시지를 받아야 하는지 확인
        required_from = {
            "logi-agent": ["req-agent"],
            "phys-agent": ["req-agent", "logi-agent"],
            "cons-agent": ["phys-agent"],
        }
        
        sources = required_from.get(agent_name, [])
        for source in sources:
            msg_path = self.project.prompt_path(iteration, source, agent_name)
            if not msg_path.exists():
                print(f"  [CHECK] Missing: {msg_path}")
                return False
        return True
    
    def _gather_inputs(self, iteration: int, agent_name: str) -> str:
        """
        Agent에게 필요한 모든 입력 파일(메시지)을 읽어서 합침.
        이것이 "파일 기반 메시지 수신"의 실체입니다.
        """
        required_from = {
            "logi-agent": ["req-agent"],
            "phys-agent": ["req-agent", "logi-agent"],
            "cons-agent": ["phys-agent"],
        }
        
        sources = required_from.get(agent_name, [])
        combined = []
        
        for source in sources:
            msg_path = self.project.prompt_path(iteration, source, agent_name)
            content = msg_path.read_text(encoding="utf-8")
            combined.append(f"## Input from {source}\n\n{content}")
            print(f"  [READ] {agent_name} ← {source}: {msg_path}")
        
        return "\n\n---\n\n".join(combined)
    
    def _validate_output(self, iteration: int, agent_name: str) -> bool:
        """산출물 파일이 제대로 생성되었는지 검증"""
        output = self.project.output_path(iteration, agent_name)
        if not output.exists():
            return False
        content = output.read_text(encoding="utf-8")
        if len(content.strip()) < 50:  # 너무 짧으면 실패로 간주
            return False
        return True
    
    def _summarize_iteration(self, iteration: int):
        """iteration 완료 후 전체 산출물 목록 출력"""
        iter_dir = self.project.base / "iterations" / f"iter-{iteration}"
        print(f"\n--- Iteration {iteration} artifacts ---")
        for path in sorted(iter_dir.rglob("*.md")):
            relative = path.relative_to(iter_dir)
            size = path.stat().st_size
            print(f"  {relative} ({size} bytes)")


# ============================================================
# 6. 실행 예시
# ============================================================

def main():
    """
    전체 흐름 시연:
    1. 프로젝트 생성
    2. Agent 등록
    3. Iteration 1 실행
    4. 파일 시스템 확인
    """
    
    # 프로젝트 초기화
    project = ProjectStructure("./projects", "my-todo-app")
    
    # Agent 생성 및 등록
    orchestrator = CoodAgent(project)
    req_agent = RequAgent(project, llm_client=None)  # 실제로는 Claude API client
    
    orchestrator.register_agent("req-agent", req_agent)
    # orchestrator.register_agent("logi-agent", LogiAgent(project))
    # orchestrator.register_agent("phys-agent", PhysAgent(project))
    # orchestrator.register_agent("cons-agent", ConsAgent(project))
    
    # Iteration 1 실행
    orchestrator.run_iteration(
        iteration=1,
        user_request="Build a simple todo app with user authentication, "
                     "task CRUD, and due date reminders."
    )
    
    # 결과 확인: 파일 시스템에 무엇이 생겼는지
    print("\n\n=== FILE SYSTEM STATE (= Message State) ===")
    for path in sorted(project.base.rglob("*.md")):
        print(f"  {path.relative_to(project.base)}")


if __name__ == "__main__":
    main()
