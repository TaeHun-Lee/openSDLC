# TODO: Smart Merge Engine 도입 (Partial Code Update)

`CodeAgent`가 소스 코드 전체를 반환하는 대신, 변경이 필요한 부분만 **'Search & Replace'** 방식으로 출력하고 백엔드에서 이를 안전하게 병합하는 메커니즘을 도입한다.

## 1. 개요 (Objective)
- **문제점:** 파일이 커질수록 LLM의 출력 토큰 제한(예: 8,192 토큰)에 걸려 `ImplementationArtifact` YAML이 누락되거나 코드가 잘리는 현상 발생.
- **해결책:** 기존 파일을 읽고 수정할 부분만 기술하는 'Search-Replace' 프로토콜을 백엔드에 구현하여 토큰 효율과 작업 안정성을 동시에 확보.

---

## 2. LLM 병합 프로토콜 (The Search-Replace Protocol)

모든 LLM 모델(CodeAgent)은 소스 코드를 수정할 때 다음의 마커 구조를 사용해야 한다.

### 출력 형식 규칙
- 각 파일은 기존과 동일하게 `<!-- FILE: {relative_path} -->` 마커로 시작한다.
- 파일 내용(코드 블록)은 전체를 다시 쓰는 대신, 하나 이상의 `Search-Replace` 블록을 포함할 수 있다.
- 변경이 없는 파일은 출력에서 제외한다.

### Search-Replace 블록 구조
```python
<<<< SEARCH
{기존 파일에 존재하는 정확한 코드 블록}
====
{새롭게 대체될 코드 블록}
>>>> REPLACE
```

### 필수 준수 사항
1. **정확한 일치:** `SEARCH` 섹션의 코드는 기존 파일의 내용(공백, 들여쓰기 포함)과 **100% 일치**해야 한다.
2. **고유성:** `SEARCH` 섹션은 파일 내에서 유일하게 식별될 수 있는 충분한 컨텍스트를 포함해야 한다.
3. **순차 적용:** 하나의 파일에 여러 블록이 있을 경우, 위에서 아래 방향으로 순차 적용된다.

---

## 3. 백엔드 병합 엔진 설계 (Backend Merge Engine)

`backend/app/core/artifacts/code_extractor.py`의 `write_code_blocks` 함수를 다음과 같이 고도화한다.

### 로직 흐름 (Algorithm)
1. **입력 분석:** `code_blocks` 내의 `content`가 `<<<< SEARCH` 마커를 포함하는지 확인.
2. **전체 쓰기 모드 (Fallback):** 마커가 없으면 기존 방식대로 전체 덮어쓰기 수행.
3. **부분 수정 모드 (Merge):**
   - 기존 파일 내용을 로드한다.
   - `SEARCH` 블록을 찾아 `REPLACE` 내용으로 치환한다.
   - 치환 실패 시(원본 불일치 등) 에러를 발생시키고 해당 파일을 건너뛴 후, `ValidatorAgent`에게 피드백을 전달할 수 있도록 로깅한다.
4. **결과 저장:** 병합된 결과물을 파일에 쓰고 백업(.bak)을 생성한다.

---

## 4. 구현 작업 목록 (Implementation Tasks)

### [Task 1] `code_extractor.py` 고도화
- `apply_search_replace(original_text, patch_text)` 함수 구현.
- `write_code_blocks` 내에서 `apply_search_replace` 호출 로직 추가.
- 예외 처리: `SEARCH` 블록 미검색 시 상세 에러 메시지 반환.

### [Task 2] `CodeAgent` 프롬프트(Override) 수정
- `backend/agent-config-overrides/CodeAgent.override.yaml`에 Search-Replace 프로토콜 지침 추가.
- "기존 파일이 이미 존재할 경우, Search-Replace 방식을 우선적으로 사용하여 토큰 소모를 최소화하라"는 지시 명시.
- 예시(Few-shot) 제공:
  ```
  <!-- FILE: app.py -->
  ```python
  <<<< SEARCH
  @app.route('/')
  def index():
      return "Hello World"
  ====
  @app.route('/')
  def index():
      return render_template('dashboard.html')
  >>>> REPLACE
  ```

### [Task 3] `ValidatorAgent` 검증 로직 추가
- `ValidatorAgent`가 `CodeAgent`의 Search-Replace 블록이 기술적으로 유효한지(마커 짝이 맞는지 등)를 형식 검증 단계에서 체크하도록 보강.

---

## 5. 기대 효과 (Expected Outcomes)
- **안정성:** 수만 라인의 거대 파일도 특정 함수만 안전하게 수정 가능.
- **성능:** LLM 응답 속도 향상 및 비용(토큰) 절감.
- **품질:** `CodeAgent`가 출력 제한에 걸려 아티팩트 생성을 누락하는 현상을 근본적으로 차단.
