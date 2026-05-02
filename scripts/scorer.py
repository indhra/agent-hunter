"""
scorer.py — Score and rank HuntResult objects by relevance.

Scoring formula (v0.2.1+):
    total = (stack_match  × 0.30
           + domain_match × 0.20
           + star_score   × 0.15
           + recency      × 0.15
           + trust_score  × 0.20) × yagni_multiplier

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
    "stack_match":   0.30,
    "domain_match":  0.20,
    "star_score":    0.15,
    "recency_score": 0.15,
    "trust_score":   0.20,
}

YAGNI_MULTIPLIERS = {
    "active":  2.0,
    "recent":  1.0,
    "dormant": 0.5,
    "unknown": 1.0,
}

TRUST_TIER_SCORES = {
    "verified":  1.0,
    "community": 0.7,
    "raw":       0.4,
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
    domain_match_score: float = 0.0
    star_score: float = 0.0
    recency_score: float = 0.0
    trust_score: float = 0.0
    yagni_multiplier: float = 1.0

    explanation: str = ""   # "why this for you" sentence, set by host agent


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
    s.stack_match_score = _compute_stack_match(r, meta, profile)

    # --- Domain match (0.0 – 1.0) ---
    s.domain_match_score = _compute_domain_match(r, meta, profile)

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
        s.stack_match_score  * w["stack_match"]
        + s.domain_match_score * w["domain_match"]
        + s.star_score         * w["star_score"]
        + s.recency_score      * w["recency_score"]
        + s.trust_score        * w["trust_score"]
    )
    s.total_score = min(raw * s.yagni_multiplier, 1.0)

    return s


def _compute_stack_match(
    r: HuntResult,
    meta: Optional[SkillMetadata],
    profile: ContextProfile,
) -> float:
    """How well does this skill's tech stack overlap with the project's?"""
    if not profile.tech_stack:
        return 0.5  # no context = neutral

    # Use skill name + description + repo name as proxy when full body unavailable
    text = f"{r.name} {r.description} {r.repo_name}".lower()
    if meta:
        text += f" {meta.description} {meta.body[:500]}".lower()

    matches = sum(1 for t in profile.tech_stack if t in text)
    return min(matches / max(len(profile.tech_stack), 1), 1.0)


def _compute_domain_match(
    r: HuntResult,
    meta: Optional[SkillMetadata],
    profile: ContextProfile,
) -> float:
    """How well does this skill's domain match the project's domain tags?"""
    if not profile.domain_tags:
        return 0.5

    text = f"{r.name} {r.description} {r.repo_name}".lower()
    if meta:
        text += f" {meta.description}".lower()

    matches = sum(1 for d in profile.domain_tags if d in text)
    return min(matches / max(len(profile.domain_tags), 1), 1.0)


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
    """YAGNI multiplier: reward skills that match domains actively in use."""
    # Check if this skill's tech overlaps with the project's active domains
    text = f"{r.name} {r.repo_name}".lower()
    if any(t in text for t in profile.active_domains):
        return YAGNI_MULTIPLIERS["active"]
    if any(t in text for t in profile.recent_domains):
        return YAGNI_MULTIPLIERS["recent"]
    if profile.dormant_domains and any(t in text for t in profile.dormant_domains):
        return YAGNI_MULTIPLIERS["dormant"]
    return YAGNI_MULTIPLIERS["unknown"]
