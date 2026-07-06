"""Draft registry for Jack Personal OS.

This module is intentionally not imported by the application yet.
It documents the first safe extension points for a personal decision layer.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JackToolDraft:
    id: str
    category: str
    label: str
    description: str
    risk_level: str = "read"
    read_only: bool = True
    enabled: bool = False
    safety: str = "No runtime side effects in v1."


JACK_PERSONAL_OS_TOOLS: tuple[JackToolDraft, ...] = (
    JackToolDraft(
        id="jack.setup_scan",
        category="jack",
        label="Jack setup scan",
        description="Score a symbol against Jack's personal setup checklist.",
    ),
    JackToolDraft(
        id="jack.risk_check",
        category="jack",
        label="Jack risk check",
        description="Check a candidate idea against the current personal risk mode.",
    ),
    JackToolDraft(
        id="jack.size_calc",
        category="jack",
        label="Jack size calculator",
        description="Calculate allowed size from account stage, risk mode, and setup quality.",
    ),
    JackToolDraft(
        id="jack.plan_draft",
        category="jack",
        label="Jack plan draft",
        description="Create a reviewable plan draft for the user to approve manually.",
        risk_level="write_draft",
        read_only=False,
    ),
    JackToolDraft(
        id="jack.journal_draft",
        category="jack",
        label="Jack journal draft",
        description="Create a reviewable journal draft for later review.",
        risk_level="write_draft",
        read_only=False,
    ),
    JackToolDraft(
        id="jack.memory_lookup",
        category="jack",
        label="Jack memory lookup",
        description="Read past lessons and mistake patterns for context.",
    ),
)
