"""Message segment processing and validation.

This module handles message segment normalization, validation, and result creation
for the AssistReply workflow.
"""

import re as _re
from typing import Callable, List

from llama_index.core.workflow import StopEvent

from app.schemas.ask_ai.auto_response import MessageSegment, AutoResponseResultDto
from app.schemas.ask_ai.ticket import Ticket


def normalize_segments(
    segments: List[any], extract_fn: Callable[[str], tuple[str, list[dict]]]
) -> List[MessageSegment]:
    """Normalize message segments by extracting images and cleaning text.

    Args:
        segments: Raw segments from LLM output
        extract_fn: Function to extract image URLs from text (returns (cleaned_text, attachments))

    Returns:
        List of normalized MessageSegment objects
    """
    cleaned: List[MessageSegment] = []
    for seg in segments:
        text = getattr(seg, "content", "") or ""
        cleaned_text, auto_atts = extract_fn(text)
        cleaned_text = _re.sub(r"[`*_#>]+", "", cleaned_text).strip()

        validated: List[dict] = []
        for att in list(getattr(seg, "attachments", []) or []) + list(auto_atts or []):
            if isinstance(att, dict):
                att_url = att.get("url", "")
                att_name = att.get("name", "")
                att_type = att.get("type", "image")
            else:
                att_url = getattr(att, "url", "")
                att_name = getattr(att, "name", "")
                att_type = getattr(att, "type", "image")

            if att_name:
                if att_url:
                    ext_match = _re.search(r"\.(\w+)(?:\?|$)", att_url)
                    ext = ext_match.group(1) if ext_match else "jpg"
                    if "." not in att_name:
                        att_name = f"{att_name}.{ext}"
                else:
                    att_name = f"product_{len(validated) + 1}.jpg"
            else:
                ext_match = _re.search(r"\.(\w+)(?:\?|$)", att_url) if att_url else None
                ext = ext_match.group(1) if ext_match else "jpg"
                att_name = f"product_{len(validated) + 1}.{ext}"

            validated.append({"type": att_type, "url": att_url, "name": att_name})

        cleaned.append(
            MessageSegment(
                content=cleaned_text,
                order=getattr(seg, "order", 0) or 0,
                delay_ms=getattr(seg, "delay_ms", 0) or 0,
                type=getattr(seg, "type", "text"),
                attachments=validated,
            )
        )
    return cleaned


def validate_segments(segments: list[MessageSegment]) -> list[MessageSegment]:
    """Validate and clean message segments.

    Ensures segments have proper ordering, delays, and at least one segment exists.

    Args:
        segments: List of message segments to validate

    Returns:
        Validated list of message segments (guaranteed non-empty)
    """
    if not segments:
        return [MessageSegment(content="", order=1, delay_ms=0, type="text")]

    # Set proper ordering
    for idx, seg in enumerate(segments, start=1):
        seg.order = idx

    # First segment has no delay
    if segments:
        segments[0].delay_ms = 0

    # Validate delays
    for seg in segments:
        if seg.delay_ms < 0:
            seg.delay_ms = 0
        elif seg.delay_ms > 5000:
            seg.delay_ms = 1000

    # Filter out empty segments
    segments = [seg for seg in segments if seg.content or seg.attachments]

    # Ensure at least one segment
    return segments if segments else [
        MessageSegment(
            content="Xin lỗi, tôi cần thêm thông tin để trả lời.",
            order=1,
            delay_ms=0,
            type="text",
        )
    ]


def create_stop_event_result(
    messages: list[MessageSegment],
    ticket: Ticket,
    agent_can_reply: bool,
    skip_response: bool,
    should_skip: bool = False,
    reason: str = "",
) -> StopEvent:
    """Create a StopEvent result for workflow completion.

    Args:
        messages: List of message segments for the response
        ticket: Ticket information
        agent_can_reply: Whether agent can handle this ticket
        skip_response: Whether to skip sending the response
        should_skip: Whether workflow should skip (for triage)
        reason: Reason for skipping (if should_skip is True)

    Returns:
        StopEvent with formatted result
    """
    result = AutoResponseResultDto(
        response=messages,
        ticket=ticket,
        agent_can_reply=agent_can_reply,
        skipResponse=skip_response,
    )

    event_result = {
        "response": [msg.dict() for msg in messages],
        "ticket": result.ticket.dict(),
        "agent_can_reply": result.agent_can_reply,
        "skipResponse": result.skipResponse,
    }

    if should_skip:
        event_result.update({"should_skip": should_skip, "reason": reason})

    return StopEvent(result=event_result)
