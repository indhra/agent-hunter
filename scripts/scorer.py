"""
scorer.py — Score and rank HuntResult objects by relevance.

Scoring formula (v1.0.0-alpha, 4-signal):
    total = (stack_match   × 0.40
           + trust_score   × 0.30
           + recency_score × 0.15
           + star_score    × 0.15) × yagni_multiplier

    YAGNI multiplier:
        active  (commits in last 7d):  2.0×
        recent  (commits in last 30d): 1.0×
        dormant (no commits in 90+d):  0.5×

    Trust tier scores:
        verified:  1.0
        community: 0.7
        raw:       0.4

Input:  List[HuntResult], ContextProfile
Output: List[ScoredResult] sorted descending by total_score

No LLM calls. No network access.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from context_extractor import ContextProfile
from hunter import HuntResult
from skill_parser import SkillMetadata


# ---------------------------------------------------------------------------
# Weights (mirrors config/defaults.json — update both if changing)
# ---------------------------------------------------------------------------

WEIGHTS = {
    "stack_match": 0.40,
    "trust_score": 0.30,
    "recency_score": 0.15,
    "star_score": 0.15,
}

YAGNI_MULTIPLIERS = {
    "active": 2.0,
    "recent": 1.0,
    "dormant": 0.5,
    "unknown": 1.0,
}

TRUST_TIER_SCORES = {
    "verified": 1.0,
    "community": 0.7,
    "raw": 0.4,
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ScoredResult:
    hunt_result: HuntResult
    skill_metadata: Optional[SkillMetadata]

    total_score: float = 0.0
    stack_match_score: float = 0.0
    star_score: float = 0.0
    recency_score: float = 0.0
    trust_score: float = 0.0
    yagni_multiplier: float = 1.0

    explanation: str = ""  # "why this for you" sentence, set by host agent


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


def score_results(
    results: list[HuntResult],
    profile: ContextProfile,
    metadata_map: Optional[dict[str, SkillMetadata]] = None,
    config: Optional[dict] = None,
) -> list[ScoredResult]:
    """Score and rank a list of HuntResult objects.

    Args:
        results: Raw HuntResult list from hunter.py.
        profile: ContextProfile from context_extractor.py.
        metadata_map: Optional dict mapping repo_url → SkillMetadata.
                      Provides richer stack/trigger matching if available.
        config: Optional merged config dict (from defaults.json + user config).
                When provided, scoring weights are read from
                config['scoring']['weights'], falling back to module-level
                WEIGHTS if the key is absent.

    Returns:
        List of ScoredResult, sorted descending by total_score.
    """
    weights = WEIGHTS
    if config:
        weights = config.get("scoring", {}).get("weights", WEIGHTS)

    metadata_map = metadata_map or {}
    scored = []

    for r in results:
        meta = metadata_map.get(r.repo_url)
        s = _score_single(r, meta, profile, weights)
        scored.append(s)

    return sorted(scored, key=lambda s: s.total_score, reverse=True)


def _score_single(
    r: HuntResult,
    meta: Optional[SkillMetadata],
    profile: ContextProfile,
    weights: Optional[dict] = None,
) -> ScoredResult:
    """Compute the full score for a single result."""
    w = weights if weights is not None else WEIGHTS
    s = ScoredResult(hunt_result=r, skill_metadata=meta)

    # --- Stack match (0.0 – 1.0) ---
    # Combines tech stack, domain tags, and intent keywords into one signal
    s.stack_match_score = _compute_stack_match(r, meta, profile)

    # --- Star score: log-normalized, cap at 10k stars = 1.0 ---
    s.star_score = min(math.log10(max(r.stars, 1)) / 4.0, 1.0)

    # --- Recency score (0.0 – 1.0) ---
    s.recency_score = _compute_recency(r)

    # --- Trust score ---
    s.trust_score = TRUST_TIER_SCORES.get(r.trust_tier, 0.4)

    # --- YAGNI multiplier ---
    s.yagni_multiplier = _compute_yagni(r, profile)

    # --- Total ---
    raw = (
        s.stack_match_score * w["stack_match"]
        + s.star_score * w["star_score"]
        + s.recency_score * w["recency_score"]
        + s.trust_score * w["trust_score"]
    )
    s.total_score = min(raw * s.yagni_multiplier, 1.0)

    return s


def _compute_stack_match(
    r: HuntResult,
    meta: Optional[SkillMetadata],
    profile: ContextProfile,
) -> float:
    """How well does this skill match the project's tech stack, domain, and intent?

    Combines:
    - Tech stack overlap (framework/library names)
    - Domain tags (web, ml, cli, etc.)
    - Intent keywords (if provided by user)
    - Purpose filtering (Bug #2 fix: exclude non-helper skills)

    All signals are folded into one unified "does it fit my project?" score.
    """
    if not profile.tech_stack and not profile.domain_tags:
        return 0.5  # no context = neutral

    # Build text corpus from skill
    text = f"{r.name} {r.description} {r.repo_name}".lower()
    if meta:
        text += f" {meta.description} {meta.body[:500]}".lower()

    # Bug #2 fix: Exclude obvious mismatches (spell checkers, dictionaries, UI components, etc.)
    # These match keywords but aren't actually helpful for development
    mismatch_patterns = [
        "spell",
        "spellcheck",
        "cspell",
        "dictionary",
        "dict-",
        "storybook",
        "figma",
        "sketch",
        "design-system",
        "is-",
        "has-",
        "check-",
        "-checker",  # runtime type checkers, not dev helpers
        "logo",
        "icon",
        "font",
        "theme",
    ]

    # If skill name/description contains mismatch patterns, penalize heavily
    mismatch_count = sum(1 for pattern in mismatch_patterns if pattern in text)
    if mismatch_count > 0:
        # Strong signal that this is not a development helper
        return 0.1  # Very low score, almost filtered out

    # Count matches across all signals
    total_signals = []
    matched_signals = []

    # Tech stack signals
    if profile.tech_stack:
        total_signals.extend(profile.tech_stack)
        matched_signals.extend([t for t in profile.tech_stack if t in text])

    # Domain signals
    if profile.domain_tags:
        total_signals.extend(profile.domain_tags)
        matched_signals.extend([d for d in profile.domain_tags if d in text])

    # Intent signals (if provided)
    if hasattr(profile, "intent_keywords") and profile.intent_keywords:
        total_signals.extend(profile.intent_keywords)
        matched_signals.extend([kw for kw in profile.intent_keywords if kw in text])

    if not total_signals:
        return 0.5

    # Bug #2 fix: Bonus for PURPOSE indicators (helps, builds, generates, tests, etc.)
    purpose_indicators = [
        "help",
        "build",
        "generate",
        "test",
        "create",
        "manage",
        "deploy",
        "monitor",
        "debug",
        "analyze",
        "optimize",
        "automate",
        "skill",
        "mcp",
        "agent",
        "tool",  # Generic skill/agent/tool indicators
    ]
    has_purpose = any(indicator in text for indicator in purpose_indicators)

    # Calculate base match ratio
    match_ratio = len(matched_signals) / len(total_signals)

    # Boost score if skill demonstrates clear purpose
    if has_purpose:
        match_ratio = min(match_ratio * 1.2, 1.0)  # 20% bonus for purpose clarity

    return min(match_ratio, 1.0)


def _compute_recency(r: HuntResult) -> float:
    """Score recency: 1.0 for commits today, 0.0 for 180+ days ago."""
    if r.last_commit_date is None:
        return 0.5  # unknown = neutral

    # last_commit_date may be a datetime object or an ISO string
    date = r.last_commit_date
    if isinstance(date, str):
        try:
            date = datetime.fromisoformat(date.rstrip("Z"))
        except ValueError:
            return 0.5

    # Normalise to naive UTC for consistent arithmetic
    if date.tzinfo is not None:
        date = date.replace(tzinfo=None)

    age_days = (datetime.now(timezone.utc).replace(tzinfo=None) - date).days
    if age_days <= 0:
        return 1.0
    if age_days >= 180:
        return 0.0
    return 1.0 - (age_days / 180.0)


def _compute_yagni(r: HuntResult, profile: ContextProfile) -> float:
    """
    YAGNI multiplier: reward skills matching domains actively in use.

    Checks git activity signals to detect:
    - Active domains (commits in last 7d) → 2.0×
    - Recent domains (commits in last 30d) → 1.0×
    - Dormant domains (no commits in 90+d) → 0.5×
    """
    text = f"{r.name} {r.repo_name}".lower()

    # Check git activity signals
    if hasattr(profile, "active_domains") and any(t in text for t in profile.active_domains):
        return YAGNI_MULTIPLIERS["active"]

    if hasattr(profile, "recent_domains") and any(t in text for t in profile.recent_domains):
        return YAGNI_MULTIPLIERS["recent"]

    if hasattr(profile, "dormant_domains") and any(t in text for t in profile.dormant_domains):
        return YAGNI_MULTIPLIERS["dormant"]

    return YAGNI_MULTIPLIERS["unknown"]
