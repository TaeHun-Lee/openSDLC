# AGENTS.md

This file defines repository-local agent instructions for `open-sdlc-v1`.

## 1. Purpose
- This repository is the source of truth for `OpenSDLC v1` constitution, engine core concepts, agent prompts, artifact templates, and related runtime workflow rules.
- Any agent working in this repository MUST preserve OpenSDLC as an `Artifact-Driven Execution` system governed by `Validation Over Self-Assertion`, `Full Traceability`, `Strict Adherence`, `No-Shortcut Principle`, and `Sequential Single-Agent Execution`.

## 2. Rule of Precedence
- Higher-level platform `system` instructions override this file.
- Higher-level platform `developer` instructions override this file.
- Within this repository, this `AGENTS.md` is the default local operating rule unless the user explicitly instructs otherwise.
- When the user explicitly requests that OpenSDLC workflow documents be applied, agents MUST treat OpenSDLC as the active repository execution mode, subject only to higher-level platform constraints.

## 3. Default Reference Scope
- Default authoritative reference scope:
  - `open-sdlc-constitution/`
  - `open-sdlc-engine/core-concepts/`
  - `open-sdlc-engine/prompts/`
  - `open-sdlc-engine/templates/`
- `open-sdlc-docs/` is NOT part of the default execution context.
- `open-sdlc-docs/` contains analysis, diary, planning, and proposal materials and MUST NOT be consulted, cited, or treated as binding unless the user explicitly requests work involving that folder.

## 4. OpenSDLC Preservation Mandate
- Agents MUST preserve the following OpenSDLC invariants unless the user explicitly instructs a redesign:
  - `Artifact-Driven Execution`
  - `Spiral Iteration`
  - `Human-Guided Development`
  - `Strict Adherence`
  - `Full Traceability`
  - `Role-Based Orchestration`
  - `Validation Over Self-Assertion`
  - `No-Shortcut Principle`
  - `Sequential Single-Agent Execution`
  - `PMAgent Exclusive User Interaction`
- Agents MUST NOT weaken, blur, or silently bypass these invariants through convenience edits, wording simplification, prompt compression, schema shortcuts, or undocumented interpretation.

## 5. Sequential Single-Agent Execution
- OpenSDLC in this repository MUST be treated as a runtime workflow model, not merely a documentation style.
- At any given moment, exactly ONE OpenSDLC agent is active.
- Agents do NOT run in parallel.
- Agents MUST NOT describe, imply, or simulate multiple agents as concurrently active.
- Agents MUST NOT rewrite repository content in ways that legitimize parallel agent execution, blended handoff ownership, or multi-phase batching as normal behavior.
- If a repository change would alter execution order, handoff semantics, validation timing, or reporting ownership, the change MUST be explicit and internally propagated across all affected documents.

## 6. No-Shortcut Principle
- The artifact pipeline MUST remain explicit, sequential, and validator-gated.
- The canonical pipeline is:
  - `User Story`
  - `UseCaseModelArtifact (UC)`
  - `ValidationReportArtifact (VAL)`
  - `TestDesignArtifact (TEST-DESIGN)`
  - `ValidationReportArtifact (VAL)`
  - `ImplementationArtifact (IMPL)`
  - `ValidationReportArtifact (VAL)`
  - `TestReportArtifact (TEST-EXECUTION)`
  - `ValidationReportArtifact (VAL)`
  - `FeedbackArtifact (FB)`
  - `ValidationReportArtifact (VAL)`
  - `verification_report.md`
- `TEST-DESIGN` MUST remain before implementation.
- `TEST-EXECUTION` MUST remain after implementation.
- Agents MUST NOT introduce documentation or prompt changes that merge, skip, hide, or redefine these stages without an explicit user-directed redesign.

## 7. Role-Based Orchestration
- Repository changes MUST preserve the distinct authority boundaries of:
  - `PMAgent`
  - `ReqAgent`
  - `CodeAgent`
  - `TestAgent`
  - `CoordAgent`
  - `ValidatorAgent`
- `PMAgent` is the sole user interaction interface for input requests and approval requests.
- `ReqAgent` defines requirements and MUST NOT be reframed as an implementation agent.
- `CodeAgent` implements approved requirements and approved test design only.
- `TestAgent` owns both `Design Mode` and `Execution Mode` but MUST remain bound to approved artifacts.
- `CoordAgent` converts approved test findings into next-iteration guidance and MUST NOT become a direct implementation commander.
- `ValidatorAgent` is an independent gatekeeper and MUST NOT be reframed as a silent fixer or substitute author.

## 8. Validation Over Self-Assertion
- Repository content MUST preserve the rule that specialized agents do not self-approve their own artifacts.
- Every stage artifact MUST remain independently auditable by `ValidatorAgent`.
- Agents MUST prefer explicit validation checks over vague claims of correctness.
- Agents MUST preserve or strengthen checks related to:
  - `schema`
  - `traceability`
  - `evidence`
  - `decision_consistency`
  - `role_boundary`
  - `no_regression`
- If a change creates ambiguity between producer claims and validator authority, the repository MUST be corrected in favor of independent validation.

## 9. Full Traceability
- Agents MUST preserve end-to-end traceability across:
  - `UseCaseModelArtifact`
  - `TestDesignArtifact`
  - `ImplementationArtifact`
  - `TestReportArtifact`
  - `FeedbackArtifact`
  - `ValidationReportArtifact`
- `source_artifact_ids`, stage references, defect mappings, test scenario mappings, and handoff targets MUST remain internally consistent.
- Agents MUST NOT remove traceability fields, weaken traceability requirements, or replace evidence-based linkage with informal prose.

## 10. Artifact and Template Discipline
- Artifact templates under `open-sdlc-engine/templates/` are schema contracts.
- Agents MUST treat template structure as mandatory.
- Required keys MUST NOT be removed.
- Optional values may be empty only when the schema and workflow allow emptiness.
- When changing template fields, agents MUST update all dependent prompts and concept documents needed to keep the repository internally consistent.
- Agents MUST use exact artifact terminology already established by the repository, including:
  - `UseCaseModelArtifact`
  - `TestDesignArtifact`
  - `ImplementationArtifact`
  - `TestReportArtifact`
  - `FeedbackArtifact`
  - `ValidationReportArtifact`

## 11. Strict Adherence for Repository Edits
- Make the smallest change that fully satisfies the user's request.
- Do NOT add speculative behavior, process expansion, new exceptions, or creative reinterpretation unless explicitly requested.
- Do NOT silently modernize terminology if that would drift from existing OpenSDLC language.
- Do NOT normalize away distinctions that the repository intentionally keeps explicit, such as:
  - `TEST-DESIGN` vs `TEST-EXECUTION`
  - `warning` vs `fail`
  - `actionable` vs `completed`
  - reporting vs approval
  - feedback for `ReqAgent` vs direct orders to `CodeAgent`

## 12. Consistency Repair Obligation
- If constitution, core concepts, prompts, templates, or reports contradict one another, agents SHOULD surface and fix the contradiction explicitly when it is within task scope.
- Agents MUST NOT silently choose one layer and leave repository-wide contradictions unresolved when the requested work depends on that inconsistency.
- Constitution-level terminology and invariants should be treated as highly stable and changed only intentionally.

## 13. Reporting and Review Expectations
- When explaining repository changes, agents SHOULD describe the impact in terms of:
  - workflow behavior
  - artifact contract impact
  - validation gate impact
  - traceability impact
- If the user requests a review, findings MUST prioritize:
  - process non-compliance
  - broken role boundaries
  - validator gate regressions
  - missing or weakened traceability
  - schema or template drift
  - stage-order regressions

## 14. Repository Path Interpretation
- `open-sdlc-constitution/` contains the top-level normative rules.
- `open-sdlc-engine/core-concepts/` contains runtime operating concepts and workflow semantics.
- `open-sdlc-engine/prompts/` contains agent-level operational instructions.
- `open-sdlc-engine/templates/` contains artifact and report schema contracts.
- `open-sdlc-docs/` remains out of default scope unless explicitly requested by the user.

## 15. Practical Authoring Defaults
- Preserve established OpenSDLC terminology exactly where practical.
- Keep markdown precise, scannable, and operational.
- Prefer ASCII by default, except where existing files already use Korean or mixed-language wording naturally.
- When duplication across OpenSDLC documents is necessary, agents SHOULD keep wording synchronized rather than approximately aligned.
