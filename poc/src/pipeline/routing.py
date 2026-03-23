"""Routing functions for dynamic pipeline conditional edges."""

from __future__ import annotations

import logging

from pipeline.state import PipelineState

logger = logging.getLogger(__name__)


def make_validator_router(step_num: int):
    """Create a routing function for a ValidatorAgent step.

    Returns a closure that reads the latest validation result from state.
    Routes: "pass" | "rework" | "max_retries"

    Uses rework_count (per-gate) to decide rework vs max_retries.
    """

    def route_after_validation(state: PipelineState) -> str:
        latest_step = state["steps_completed"][-1] if state["steps_completed"] else None
        result = latest_step["validation_result"] if latest_step else "fail"
        rework_count = state["rework_count"]
        max_reworks = state["max_reworks_per_gate"]

        if result == "pass":
            logger.info(
                "[Router] step %d: validation=pass → next step", step_num
            )
            return "pass"

        if rework_count >= max_reworks:
            logger.warning(
                "[Router] step %d: validation=%s, max_reworks_per_gate=%d reached → END",
                step_num,
                result,
                max_reworks,
            )
            return "max_retries"

        logger.info(
            "[Router] step %d: validation=%s, rework=%d/%d → rework",
            step_num,
            result,
            rework_count,
            max_reworks,
        )
        return "rework"

    route_after_validation.__name__ = f"route_step_{step_num}"
    return route_after_validation
