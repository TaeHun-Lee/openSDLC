"""Parse structured reporting events from agent narrative text."""

from __future__ import annotations

import re

from app.core.pipeline.state import ReportingEvent

_AGENT_LINE_RE = re.compile(r"\[(\w+(?:Agent)?)\]\s*(.+)")

_START_KEYWORDS = ("시작", "start", "시작합니다", "시작하겠습니다", "분석을 시작", "작업을 시작")
_COMPLETE_KEYWORDS = ("완료", "complete", "생성이 완료", "작성이 완료", "작업을 완료")
_HANDOFF_KEYWORDS = ("다음", "handoff", "넘기", "요청하겠습니다", "전달하겠습니다", "검증을 요청")
_BLOCKER_KEYWORDS = ("fail", "반려", "blocker", "차단", "blocking")


def parse_reporting_events(narrative: str) -> list[ReportingEvent]:
    """Parse agent narrative text into structured reporting events."""
    if not narrative:
        return []

    events: list[ReportingEvent] = []

    for line in narrative.splitlines():
        line = line.strip()
        if not line:
            continue

        m = _AGENT_LINE_RE.match(line)
        if not m:
            continue

        agent_id = m.group(1)
        message = m.group(2)
        msg_lower = message.lower()

        event_type = _classify_event(msg_lower)
        if event_type is None:
            continue

        event = ReportingEvent(
            event_type=event_type,
            agent_id=agent_id,
            message=line,
        )

        if event_type == "handoff":
            target = _extract_handoff_target(message)
            if target:
                event["target_agent"] = target

        events.append(event)

    return events


def _classify_event(msg_lower: str) -> str | None:
    if any(kw in msg_lower for kw in _BLOCKER_KEYWORDS):
        return "blocker_detected"
    if any(kw in msg_lower for kw in _HANDOFF_KEYWORDS):
        return "handoff"
    if any(kw in msg_lower for kw in _COMPLETE_KEYWORDS):
        return "artifact_completed"
    if any(kw in msg_lower for kw in _START_KEYWORDS):
        return "stage_started"
    return None


def _extract_handoff_target(message: str) -> str | None:
    m = re.search(r"(\w+Agent)(?:에게|로|에)", message)
    if m:
        return m.group(1)
    m = re.search(r"(?:다음|next)\s+.*?(\w+Agent)", message, re.IGNORECASE)
    if m:
        return m.group(1)
    return None
