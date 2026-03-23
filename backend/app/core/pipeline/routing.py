"""Routing functions for dynamic pipeline conditional edges."""

from __future__ import annotations

import logging

from app.core.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


def make_validator_router(step_num: int):
    """Create a routing function for a ValidatorAgent step.

    Returns a closure that reads the latest validation result from state.
    Routes: "pass" | "rework" | "max_retries"
    """

    def route_after_validation(state: PipelineState) -> str:
        latest_step = state["steps_completed"][-1] if state["steps_completed"] else None
        result = latest_step["validation_result"] if latest_step else "fail"
        rework_count = state["rework_count"]
        max_reworks = state["max_reworks_per_gate"]

        if result == "pass":
            logger.info("[Router] step %d: validation=pass → next step", step_num)
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


def make_pm_iteration_router(step_num: int):
    """Create a routing function for PMAgent iteration decision.

    Reads pm_decision from state.
    Routes: "next_iteration" | "done" | "max_iterations"
    """

    def route_after_pm_assessment(state: PipelineState) -> str:
        pm_decision = state.get("pm_decision", "done")
        iteration = state["iteration_count"]
        max_iter = state["max_iterations"]

        if pm_decision == "done":
            logger.info(
                "[Router] step %d: PMAgent decision=done → END", step_num
            )
            return "done"

        # pm_decision == "continue"
        if iteration > max_iter:
            logger.warning(
                "[Router] step %d: PMAgent wants continue but iteration=%d > max=%d → END",
                step_num,
                iteration,
                max_iter,
            )
            return "max_iterations"

        logger.info(
            "[Router] step %d: PMAgent decision=continue, iteration=%d/%d → next_iteration",
            step_num,
            iteration,
            max_iter,
        )
        return "next_iteration"

    route_after_pm_assessment.__name__ = f"route_pm_step_{step_num}"
    return route_after_pm_assessment
