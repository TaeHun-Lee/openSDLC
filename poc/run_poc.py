#!/usr/bin/env python3
"""OpenSDLC entry point — dynamic pipeline runner."""

import sys
import logging
import argparse
from pathlib import Path

# Add src/ to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import LLM_PROVIDER, ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, LOG_LEVEL


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _save_artifacts(final_state: dict, out_dir: Path) -> None:
    """Save all artifacts from pipeline state."""
    out_dir.mkdir(parents=True, exist_ok=True)
    latest = final_state.get("latest_artifacts", {})

    # Save artifact YAMLs
    artifacts_dir = out_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for artifact_type, yaml_str in latest.items():
        if yaml_str:
            filename = f"{artifact_type}.yaml"
            (artifacts_dir / filename).write_text(yaml_str, encoding="utf-8")

    print(f"\n[출력] 아티팩트 저장 완료: {artifacts_dir}")
    for f in sorted(artifacts_dir.glob("*.yaml")):
        print(f"  - {f.name}")

    # Extract and write executable code files from ImplementationArtifact
    impl_yaml = latest.get("ImplementationArtifact", "")
    if impl_yaml:
        from artifacts.code_extractor import write_code_files, get_runtime_info

        workspace_dir = (out_dir / "workspace").resolve()
        written = write_code_files(impl_yaml, workspace_dir)

        if written:
            print(f"\n[출력] 실행 가능한 코드 파일 생성 완료: {workspace_dir}")
            for fpath in written:
                rel = fpath.relative_to(workspace_dir)
                size = fpath.stat().st_size
                print(f"  - {rel} ({size} bytes)")

            runtime = get_runtime_info(impl_yaml)
            if runtime.get("entrypoint"):
                print(f"\n[실행] 엔트리포인트: cd {workspace_dir} && {runtime['entrypoint']}")
            if runtime.get("test_url"):
                print(f"[실행] 테스트 URL: {runtime['test_url']}")
        else:
            print(
                "\n[경고] ImplementationArtifact에 code_files 필드가 없거나 "
                "코드 추출에 실패했습니다."
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenSDLC — LangGraph pipeline runner")
    parser.add_argument(
        "--pipeline", "-p",
        default=None,
        help="Path to pipeline YAML definition (required unless --list-agents).",
    )
    parser.add_argument(
        "--user-story", "-s",
        default=None,
        help="User story text. If omitted, reads from stdin.",
    )
    parser.add_argument(
        "--max-iterations", "-m",
        type=int,
        default=3,
        help="Maximum rework iterations before giving up (default: 3)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Save final state artifacts to this directory.",
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List all available agents in the registry and exit.",
    )
    args = parser.parse_args()

    setup_logging(LOG_LEVEL)

    # --list-agents: show available agents and exit
    if args.list_agents:
        from registry.agent_registry import load_all_agents
        agents = load_all_agents()
        print("Available Agents:")
        for agent_id, config in agents.items():
            print(f"  {agent_id:20s} — {config.role}")
            print(f"    {'':20s}   Outputs: {', '.join(config.primary_outputs)}")
        sys.exit(0)

    # Validate API key
    _KEY_MAP = {
        "anthropic": ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
        "google": ("GOOGLE_API_KEY", GOOGLE_API_KEY),
        "openai": ("OPENAI_API_KEY", OPENAI_API_KEY),
    }
    env_name, key_value = _KEY_MAP.get(LLM_PROVIDER, ("", ""))
    if not key_value:
        print(
            f"ERROR: {env_name} environment variable is not set (provider={LLM_PROVIDER}).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Require --pipeline for actual runs
    if not args.pipeline:
        parser.error("--pipeline/-p is required to run a pipeline.")

    # Read user story
    if args.user_story:
        user_story = args.user_story
    else:
        print("User Story를 입력하세요 (Ctrl+D로 완료):")
        user_story = sys.stdin.read().strip()

    if not user_story:
        print("ERROR: User story is empty.", file=sys.stderr)
        sys.exit(1)

    # Run dynamic pipeline
    from pipeline.graph_builder import load_pipeline_definition, run_pipeline

    pipeline_def = load_pipeline_definition(args.pipeline)
    if args.max_iterations != 3:
        pipeline_def.max_iterations = args.max_iterations

    final_state = run_pipeline(pipeline_def, user_story)

    if args.output:
        _save_artifacts(final_state, Path(args.output))

    # Exit with non-zero code if pipeline didn't complete successfully
    status = final_state.get("pipeline_status", "")
    if status not in ("completed",):
        print(f"\n[Pipeline] 비정상 종료 (status={status})", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
