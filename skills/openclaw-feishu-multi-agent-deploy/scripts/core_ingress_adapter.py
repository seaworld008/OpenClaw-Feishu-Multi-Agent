#!/usr/bin/env python3
"""Ingress adapter for the redesigned V5.1 control plane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InboundEvent:
    team_key: str
    source_message_id: str
    canonical_target_id: str
    request_text: str
    requested_by: str
    channel: str = "feishu"
    account_id: str = ""
    mentioned_agent_id: str = ""
    raw_event: dict[str, Any] | None = None


def canonicalize_target(raw: str | None) -> str:
    value = str(raw or "").strip()
    while value.startswith("chat:"):
        value = value[len("chat:") :].strip()
    return value


def extract_inbound_event(
    *,
    team_key: str,
    source_message_id: str,
    canonical_target_id: str,
    request_text: str,
    requested_by: str,
    channel: str = "feishu",
    account_id: str = "",
    mentioned_agent_id: str = "",
    raw_event: dict[str, Any] | None = None,
) -> InboundEvent:
    return InboundEvent(
        team_key=str(team_key).strip(),
        source_message_id=str(source_message_id).strip(),
        canonical_target_id=canonicalize_target(canonical_target_id),
        request_text=str(request_text).strip(),
        requested_by=str(requested_by).strip(),
        channel=str(channel or "feishu").strip() or "feishu",
        account_id=str(account_id or "").strip(),
        mentioned_agent_id=str(mentioned_agent_id).strip(),
        raw_event=raw_event,
    )


def persist_inbound_event(store, event: InboundEvent) -> dict[str, Any]:
    return store.record_inbound_event(
        team_key=event.team_key,
        source_message_id=event.source_message_id,
        canonical_target_id=event.canonical_target_id,
        request_text=event.request_text,
        requested_by=event.requested_by,
        raw_event=event.raw_event,
    )


def claim_inbound_event(store, *, team_key: str, source_message_id: str, job_ref: str) -> dict[str, Any] | None:
    return store.claim_inbound_event(
        team_key=team_key,
        source_message_id=source_message_id,
        job_ref=job_ref,
    )


def find_unclaimed_inbound_event_for_team(store, team_key: str) -> InboundEvent | None:
    payload = store.find_unclaimed_inbound_event_for_team(team_key)
    if payload is None:
        return None
    return extract_inbound_event(
        team_key=payload["teamKey"],
        source_message_id=payload["sourceMessageId"],
        canonical_target_id=payload["canonicalTargetId"],
        request_text=payload["requestText"],
        requested_by=payload["requestedBy"],
        channel="feishu",
        raw_event=payload.get("rawEvent"),
    )
