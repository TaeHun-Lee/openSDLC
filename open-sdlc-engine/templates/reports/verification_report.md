# OpenSDLC Verification Report (Iteration-{{iteration}})

| 정보 | 내용 |
| :--- | :--- |
| **프로젝트** | {{project_name}} |
| **생성 에이전트** | PMAgent |
| **검토 범위** | Iteration `{{iteration}}`의 UC/TEST-DESIGN/IMPL/TEST-EXECUTION/FB 및 최신 Validation 아티팩트 전체 |
| **핵심 참조** | {{artifact_reference_summary}} |
| **검증자** | PMAgent |

## 1. 규칙 및 템플릿 준수 여부 검토

### Iteration Artifact Set Compliance - {{iteration_compliance_result}}
- **네이밍 규칙**: Iteration 내 아티팩트 ID 형식이 전반적으로 올바른가? ({{naming_result}})
- **스키마 준수**: 필수 필드가 각 아티팩트에 모두 포함되어 있는가? ({{schema_result}})
- **Traceability**: 상위/하위 아티팩트 참조가 전반적으로 올바른가? ({{traceability_result}})

### Validator Gate Summary
- **UC Validation**: {{uc_validation_result}} ({{uc_validation_note}})
- **TEST-DESIGN Validation**: {{test_design_validation_result}} ({{test_design_validation_note}})
- **IMPL Validation**: {{impl_validation_result}} ({{impl_validation_note}})
- **TEST-EXECUTION Validation**: {{test_execution_validation_result}} ({{test_execution_validation_note}})
- **FB Validation**: {{fb_validation_result}} ({{fb_validation_note}})
- **Blocking Issues Remaining**: {{blocking_issue_count}}

## 2. 작업 내용 및 품질 분석

### 주요 구현/수정 사항:
- {{summary_point_1}}
- {{summary_point_2}}

### 품질 지표:
- **만족도 점수(Satisfaction Score)**: {{score}} / 100
- **결함 상태**: {{defect_count}}건 (High: {{high_count}}, Medium: {{med_count}}, Low: {{low_count}})

## 3. PMAgent 종합 의견 및 후속 조치

{{pma_comprehensive_feedback}}

### 종료 판정 우선순위
- ValidatorAgent에 `fail`이 하나라도 있으면 종료할 수 없습니다.
- ValidatorAgent의 blocking failure가 없고, 품질 기준을 충족하면 종료 권고가 가능합니다.
- 최종 프로젝트 종료는 항상 사용자 승인 이후에만 확정됩니다.

---

**사용자 가이드:**
- **실행/검토 경로**: {{runtime_reference}}
- 결정 상태: {{current_iteration_decision}}
- 판단 근거: {{decision_rationale}}
- 품질 기준 점수: {{threshold}}
- 사용자 안내: {{user_guidance_message}}
- 사용자 요청 사항: {{next_user_prompt}}
