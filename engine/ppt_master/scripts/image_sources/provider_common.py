"""Shared primitives for web image providers.

This module is the single home for everything that all four providers
(Openverse / Wikimedia / Pexels / Pixabay) need:

- License tier classification (the central abstraction of this module)
- Search request / asset candidate dataclasses
- Query simplification for keyword-based image APIs
- Candidate scoring
- Attribution text builder
- Small helpers (orientation, json path, etc.)

Provider-specific code (API URLs, payload shape, parse_results) lives in
the corresponding provider_<name>.py module and only imports from here.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from console_encoding import configure_utf8_stdio  # noqa: E402

configure_utf8_stdio()

if __name__ == "__main__":
    print(__doc__)
    print("This is an internal helper module used by image_search.py and the four web image providers.")
    raise SystemExit(0 if any(arg in {"-h", "--help", "help"} for arg in sys.argv[1:]) else 1)

import re
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Project-wide constants
# ---------------------------------------------------------------------------

USER_AGENT = "PPTMaster/1.0 (https://github.com/hugohe3/ppt-master)"


# ---------------------------------------------------------------------------
# License tier classification
# ---------------------------------------------------------------------------
#
# Every accepted candidate is classified into exactly one of two tiers:
#
#   "no-attribution"        -> No on-slide credit needed (CC0, PD, Pexels,
#                              Pixabay). Default search target.
#   "attribution-required"  -> CC BY / CC BY-SA. Executor must add an
#                              inline credit text element on the slide.
#
# Anything else (CC BY-NC, CC BY-ND, all-rights-reserved, unknown) returns
# None and the candidate is rejected outright.

LICENSE_TIER_NO_ATTRIBUTION = "no-attribution"
LICENSE_TIER_ATTRIBUTION_REQUIRED = "attribution-required"

# Tokens that mark a license as "no attribution required".
NO_ATTRIBUTION_TOKENS: tuple[str, ...] = (
    "cc0",
    "public domain",
    "publicdomain",
    "creativecommons.org/publicdomain/",
    "pexels license",
    "pixabay content license",
    "pixabay license",
)

# Tokens that mark a license as "attribution required".
ATTRIBUTION_REQUIRED_TOKENS: tuple[str, ...] = (
    "cc by",
    "cc-by",
    "by-sa",
    "by sa",
    "creativecommons.org/licenses/by/",
    "creativecommons.org/licenses/by-sa/",
)

# Tokens that disqualify a candidate entirely.
REJECTED_TOKENS: tuple[str, ...] = (
    "by-nc",
    "by nc",
    "noncommercial",
    "non-commercial",
    "by-nd",
    "by nd",
    "no derivatives",
    "noderivatives",
    "all rights reserved",
)


# Canonical display forms for license names. Different providers report
# the same license with different capitalization (Openverse: "cc0",
# Wikimedia: "Public domain"); the Executor renders these as on-slide
# text, so a normalized form prevents inconsistent credits.
_LICENSE_NAME_CANON: dict[str, str] = {
    "cc0": "CC0",
    "cc 0": "CC0",
    "public domain": "Public Domain",
    "publicdomain": "Public Domain",
    "pdm": "Public Domain",
    "pexels license": "Pexels License",
    "pixabay content license": "Pixabay Content License",
    "pixabay license": "Pixabay Content License",
}

# CC license short-name pattern used to canonicalize "cc by 4.0" → "CC BY 4.0".
_CC_PATTERN = re.compile(
    r"^\s*cc[\s-]+(by(?:[\s-]+(?:sa|nc|nd))*)\s*([0-9.]*)\s*$",
    re.IGNORECASE,
)


def normalize_license_name(name: str) -> str:
    """Return a canonical display form for a license name.

    Maps common aliases to a consistent capitalization so the on-slide
    credit text written by the Executor is uniform across providers.
    Unknown inputs are returned trimmed but otherwise unchanged.
    """
    if not name:
        return ""
    key = name.strip().lower()
    if not key:
        return ""

    if key in _LICENSE_NAME_CANON:
        return _LICENSE_NAME_CANON[key]

    cc_match = _CC_PATTERN.match(key)
    if cc_match:
        suffix_raw, version = cc_match.group(1), cc_match.group(2)
        suffix = suffix_raw.replace(" ", "-").upper()
        return f"CC {suffix} {version}".strip()

    return name.strip()


def classify_license(
    license_name: str,
    license_url: str = "",
    provider: str = "",
) -> Optional[str]:
    """Classify a license string into one of the two tiers, or reject it.

    Returns:
        ``"no-attribution"`` / ``"attribution-required"`` / ``None``.

    The provider hint lets us treat Pexels and Pixabay's own licenses as
    ``no-attribution`` even when the upstream API only returns a short
    label like ``"Pexels"``.
    """
    text = " ".join(
        part.strip().lower()
        for part in (license_name or "", license_url or "")
        if part
    )
    provider_key = (provider or "").strip().lower()

    if not text and not provider_key:
        return None

    if any(token in text for token in REJECTED_TOKENS):
        return None

    if any(token in text for token in NO_ATTRIBUTION_TOKENS):
        return LICENSE_TIER_NO_ATTRIBUTION

    # Provider-default fallback: pexels / pixabay items often arrive with a
    # bare "Pexels" / "Pixabay" license string. Their site-wide license is
    # "free for commercial use, no attribution required".
    #
    # Guard: require the license text to actually mention the provider name,
    # so an empty / missing license field never silently passes as no-attribution.
    if (
        provider_key in {"pexels", "pixabay"}
        and provider_key in text
        and not any(token in text for token in ATTRIBUTION_REQUIRED_TOKENS)
    ):
        return LICENSE_TIER_NO_ATTRIBUTION

    if any(token in text for token in ATTRIBUTION_REQUIRED_TOKENS):
        return LICENSE_TIER_ATTRIBUTION_REQUIRED

    return None  # unknown license -> reject


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ImageSearchRequest:
    """A single image search intent passed to a provider."""

    query: str
    purpose: str = ""
    orientation: str = ""  # "landscape" / "portrait" / "square" / ""
    min_width: int = 0
    min_height: int = 0
    filename: str = ""
    slide: str = ""
    required_terms: tuple[str, ...] = ()


@dataclass
class AssetCandidate:
    """One ranked candidate returned by a provider's parse_results."""

    provider: str
    title: str
    asset_id: str = ""
    source_page_url: str = ""
    license_name: str = ""
    license_url: str = ""
    license_tier: str = ""  # one of LICENSE_TIER_* constants
    width: int = 0
    height: int = 0
    download_url: str = ""
    author: str = ""
    raw: Any = field(default=None)


# ---------------------------------------------------------------------------
# Query simplification
# ---------------------------------------------------------------------------
#
# Web image APIs do keyword matching against image metadata, not semantic
# search. Long, descriptive queries with brand names, HEX codes, and
# composition notes return zero results. We progressively trim the query
# down to the most concrete nouns.

_NOISE_WORDS = frozenset({
    # Brand / product names
    "claude", "openai", "gpt", "gemini", "copilot", "chatgpt", "midjourney",
    "stable", "diffusion", "dall-e", "cursor", "anthropic", "microsoft",
    "google", "apple", "meta", "nvidia", "tesla",
    # Generic filler
    "using", "with", "from", "that", "this", "have", "been", "will",
    "into", "more", "also", "very", "some", "than", "them", "other",
})

# Words that look generic but are actually useful when they ARE the
# subject of the deck (e.g. a deck about AI). We only drop them when
# there are still other concrete nouns left.
_SOFT_NOISE_WORDS = frozenset({
    "ai", "code", "software", "system", "digital", "platform", "solution",
    "application", "interface", "framework", "algorithm", "api", "sdk",
    "assistant", "tool", "service", "technology", "tech", "program",
    # Visual-quality / usage terms. These are helpful in the full provider
    # query, but should not consume the 3-4 keyword fallback budget or
    # dominate relevance scoring over the real subject.
    "professional", "editorial", "commercial", "premium", "stock",
    "photo", "photograph", "photography", "image", "picture", "visual",
    "background", "hero", "cover", "banner", "wallpaper",
    "high", "quality", "resolution", "sharp", "clean", "cinematic",
    "dramatic", "lighting", "light", "modern", "natural", "visible",
})

_TOKEN_STRIP_CHARS = ".,;:!?\"'()[]{}，。；：！？、"
_MATCH_SEPARATOR_RE = re.compile(r"""[\s\-_./:;,'"()[\]{}]+""")

# ---------------------------------------------------------------------------
# D19 FR6.2 (PPT Engine local patch, 2026-07-03 · same precedent as svg2pptx):
# CJK-aware query handling. Upstream ppt-master treats queries as space-
# separated ASCII words, which silently mangled Chinese queries two ways:
#   1. simplify_query's ``len(w) > 2`` short-word filter dropped complete
#      2-char CJK place nouns ("福州" / "土楼");
#   2. _query_tokens dropped ALL non-ASCII tokens, zeroing the relevance
#      signal for Chinese queries (neutral 1.0 fallback let size/license
#      rescue irrelevant images).
# Range covers CJK Radicals Supplement→Unified Ideographs (U+2E80–U+9FFF)
# plus Compatibility Ideographs (U+F900–U+FAFF).
# ---------------------------------------------------------------------------
_CJK_CHAR_RE = re.compile("[\u2E80-\u9FFF\uF900-\uFAFF]")
_CJK_RUN_RE = re.compile("[\u2E80-\u9FFF\uF900-\uFAFF]+")


def _contains_cjk(text: str) -> bool:
    """True when the text has at least one CJK ideograph (D19 FR6.2)."""
    return bool(_CJK_CHAR_RE.search(text or ""))


def _cjk_scoring_tokens(word: str) -> list[str]:
    """Split one word's CJK runs into scoring tokens (D19 FR6.2).

    Chinese has no spaces: a 4-char query like "福州街景" would never
    substring-match metadata as a whole, so runs longer than 2 chars are
    broken into overlapping bigrams ("福州"/"州街"/"街景") — the minimal
    unit that still matches proper nouns. Runs of <=2 chars stay whole.
    """
    tokens: list[str] = []
    for run in _CJK_RUN_RE.findall(word or ""):
        if len(run) <= 2:
            tokens.append(run)
        else:
            tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    return tokens


def simplify_query(query: str, max_words: int = 4) -> str:
    """Trim a verbose query into a short keyword phrase.

    Strategy:
      1. Strip HEX color codes and parenthetical asides.
      2. Drop hard-noise words (brand names, generic filler).
      3. Drop soft-noise words ONLY if concrete nouns remain.
      4. If the result would be empty, return the original query
         (fail-open: better an over-broad search than zero results).
      5. Cap at ``max_words`` words.
    """
    cleaned = re.sub(r"#[0-9a-fA-F]{3,8}", "", query)
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)
    words = [w.strip(_TOKEN_STRIP_CHARS) for w in cleaned.split()]
    # D19 FR6.2: the length filter is ASCII-minded — a 2-char CJK word is a
    # complete, high-information noun ("福州"/"土楼"), keep it.
    words = [w for w in words if len(w) > 2 or _contains_cjk(w)]

    after_hard = [w for w in words if w.lower() not in _NOISE_WORDS]
    after_soft = [w for w in after_hard if w.lower() not in _SOFT_NOISE_WORDS]

    # Only drop soft-noise if there are still concrete nouns left.
    filtered = after_soft if after_soft else after_hard

    if not filtered:
        # Everything got filtered. Fail open: return the original query.
        return query.strip()

    return " ".join(filtered[:max_words])


def build_query_progression(query: str) -> list[str]:
    """Return a list of progressively simpler queries to try in order.

    Stops as soon as one of them yields candidates upstream. Duplicates
    are dropped while preserving order.
    """
    seen: set[str] = set()
    out: list[str] = []
    for candidate in (
        query,
        simplify_query(query, max_words=4),
        simplify_query(query, max_words=3),
        simplify_query(query, max_words=2),
        simplify_query(query, max_words=1),
    ):
        candidate = candidate.strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# D19 FR6.2/FR6.4 (PPT Engine local patch): provider request extras
# ---------------------------------------------------------------------------

# D19 FR6.2: CJK queries hit far more content when the provider is told the
# query language (research memo 2026-07-02: Pexels has ~4.7K Fujian-related
# photos reachable via locale=zh-CN). English queries are left untouched —
# the extra param would narrow them for no benefit.
_PROVIDER_CJK_LOCALE_PARAMS: dict[str, dict[str, str]] = {
    "pexels": {"locale": "zh-CN"},   # https://www.pexels.com/api/documentation/#photos-search
    "pixabay": {"lang": "zh"},       # https://pixabay.com/api/docs/#api_search_images
}


def cjk_locale_params(provider: str, query: str) -> dict[str, str]:
    """Extra request params for CJK queries; empty dict otherwise (D19 FR6.2).

    Only providers with a language/locale parameter are mapped; zero-config
    providers (wikimedia fulltext search / openverse) need no hint — CJK
    terms are matched directly by their search backends.
    """
    if not _contains_cjk(query):
        return {}
    return dict(_PROVIDER_CJK_LOCALE_PARAMS.get((provider or "").strip().lower(), {}))


# D19 FR6.4 (PPT Engine local patch): optional Openverse OAuth uplift.
# Anonymous Openverse is capped at ~20 req/min and 200 req/day — a real
# bottleneck across multiple decks. Registration is free and instant:
#   1. POST https://api.openverse.org/v1/auth_tokens/register/
#      with JSON {"name": "...", "description": "...", "email": "..."}
#      (or use the form at https://api.openverse.org/v1/#tag/auth)
#   2. Confirm the verification e-mail.
#   3. Put OPENVERSE_CLIENT_ID / OPENVERSE_CLIENT_SECRET into the shared
#      .env (loaded by image_search._load_search_env_file) or the process env.
# With credentials we exchange them for a bearer token (client_credentials
# grant) and attach it to search requests; without them — or on any token
# failure — everything keeps running anonymously (degrade, never block).
OPENVERSE_TOKEN_URL = "https://api.openverse.org/v1/auth_tokens/token/"
_OPENVERSE_TOKEN_CACHE: dict[str, Any] = {}


def openverse_auth_headers(timeout: int = 10) -> dict[str, str]:
    """Return ``{"Authorization": "Bearer ..."}`` when Openverse OAuth is
    configured, else ``{}`` (anonymous). Never raises (D19 FR6.4).

    The token is cached module-level until ~60s before expiry so repeated
    searches within one run don't burn extra token requests.
    """
    import os  # local import: keep the module-level surface of this vendor file unchanged
    import time

    client_id = (os.environ.get("OPENVERSE_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("OPENVERSE_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        return {}

    now = time.time()
    if _OPENVERSE_TOKEN_CACHE.get("token") and now < _OPENVERSE_TOKEN_CACHE.get("expires_at", 0.0):
        return {"Authorization": f"Bearer {_OPENVERSE_TOKEN_CACHE['token']}"}

    try:
        import requests  # local import: provider modules own the hard dependency

        response = requests.post(
            OPENVERSE_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            },
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json() or {}
        token = str(payload.get("access_token") or "").strip()
        if not token:
            return {}
        expires_in = payload.get("expires_in")
        ttl = int(expires_in) if isinstance(expires_in, (int, float)) else 600
        _OPENVERSE_TOKEN_CACHE.update(token=token, expires_at=now + max(ttl - 60, 60))
        return {"Authorization": f"Bearer {token}"}
    except Exception:
        # Rate-limit relief must never break the zero-config path: any
        # network/credential failure falls back to anonymous access.
        return {}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def normalize_orientation(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "unknown"
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def _query_tokens(query: str) -> list[str]:
    """Extract keyword tokens from a query for relevance scoring.

    Uses the same noise-word filtering as ``simplify_query`` so the
    relevance signal lines up with the keywords we actually search by.

    D19 FR6.2 (PPT Engine local patch): CJK tokens now participate in
    scoring. The upstream version dropped every non-ASCII token, so a
    Chinese query always fell back to neutral relevance (1.0) and
    size/license could rescue completely irrelevant images. CJK runs are
    tokenized via ``_cjk_scoring_tokens`` (whole word <=2 chars, else
    bigrams — Chinese has no spaces to split on); Wikimedia/Openverse
    metadata for Chinese subjects routinely carries CJK titles, so
    substring matching is reliable there. Noise-word filtering stays
    ASCII-only (the noise lists are English). When no tokens remain,
    ``compute_relevance`` falls back to neutral (1.0) as before.
    """
    cleaned = re.sub(r"#[0-9a-fA-F]{3,8}", "", query.lower())
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)
    words = [w.strip(_TOKEN_STRIP_CHARS) for w in cleaned.split()]
    ascii_words = [w for w in words if len(w) > 2 and w.isascii()]
    cjk_tokens: list[str] = []  # D19 FR6.2
    for w in words:
        cjk_tokens.extend(_cjk_scoring_tokens(w))
    if not ascii_words and not cjk_tokens:
        return []
    after_hard = [w for w in ascii_words if w not in _NOISE_WORDS]
    after_soft = [w for w in after_hard if w not in _SOFT_NOISE_WORDS]
    return (after_soft if after_soft else after_hard) + cjk_tokens


def _candidate_text(candidate: AssetCandidate) -> str:
    """Concatenate the candidate's matchable metadata fields for scoring."""
    return " ".join(
        filter(
            None,
            (
                candidate.title,
                candidate.author,
                candidate.source_page_url,
            ),
        )
    ).lower()


def _normalize_match_text(text: str) -> str:
    """Normalize metadata / required terms for conservative substring matching."""
    lowered = (text or "").lower()
    return _MATCH_SEPARATOR_RE.sub(" ", lowered).strip()


def _term_group_alternatives(term_group: str) -> list[str]:
    """Split one required term group into alternatives.

    ``"Jiefangbei|Liberation Monument"`` means either alternative satisfies
    that required group. Different list items are ANDed by
    ``missing_required_terms``.
    """
    return [
        _normalize_match_text(part)
        for part in str(term_group or "").split("|")
        if _normalize_match_text(part)
    ]


def missing_required_terms(
    candidate: AssetCandidate,
    required_terms: tuple[str, ...] | list[str] | None,
) -> list[str]:
    """Return required term groups not present in candidate metadata.

    This is an entity-safety gate, not a fuzzy visual classifier. Use it for
    exact subjects such as landmarks, people, companies, or products where a
    visually nice but wrong image is worse than no image.
    """
    if not required_terms:
        return []

    text = _normalize_match_text(_candidate_text(candidate))
    compact_text = text.replace(" ", "")
    missing: list[str] = []
    for group in required_terms:
        alternatives = _term_group_alternatives(group)
        if not alternatives:
            continue
        matched = any(
            alt in text or alt.replace(" ", "") in compact_text
            for alt in alternatives
        )
        if not matched:
            missing.append(str(group))
    return missing


def compute_relevance(candidate: AssetCandidate, query: str) -> float:
    """Fraction of query tokens that appear in the candidate's metadata.

    Range ``[0.0, 1.0]``. Returns ``1.0`` (neutral) when the query yields no
    tokens at all — since D19 FR6.2 CJK tokens participate too, so Chinese
    queries now get a real relevance signal instead of always falling
    through neutrally to license / size scoring.
    """
    tokens = _query_tokens(query)
    if not tokens:
        return 1.0
    text = _candidate_text(candidate)
    if not text:
        return 0.0
    hits = sum(1 for t in tokens if t in text)
    return hits / len(tokens)


def score_candidate(candidate: AssetCandidate, request: ImageSearchRequest) -> float:
    """Score a candidate against a request. Higher is better; -inf rejects.

    Relevance dominates: a candidate whose metadata shares no query
    tokens is rejected outright, so size / license / orientation cannot
    rescue an irrelevant image from a permissive provider.
    """
    if not candidate.license_tier:
        return float("-inf")

    required_misses = missing_required_terms(candidate, request.required_terms)
    if required_misses:
        return float("-inf")

    relevance = compute_relevance(candidate, request.query)
    if relevance == 0.0 and not request.required_terms:
        return float("-inf")

    score = relevance * 10000.0
    title_text = _normalize_match_text(candidate.title)
    compact_title = title_text.replace(" ", "")
    for group in request.required_terms or ():
        alternatives = _term_group_alternatives(group)
        if any(
            alt in title_text or alt.replace(" ", "") in compact_title
            for alt in alternatives
        ):
            score += 1500.0

    # Penalize infrastructure/transit metadata if the user didn't explicitly ask for it.
    # This prevents high-res subway station photos from outranking actual tourist landmarks.
    text = _candidate_text(candidate)
    query_lower = request.query.lower()
    infra_terms = [
        "station", "subway", "metro", "rail", "transit", "airport", "bus",
        "地铁", "站", "轨道",
    ]

    if not any(t in query_lower for t in infra_terms):
        if any(t in text for t in infra_terms):
            score -= 5000.0

    candidate_orientation = normalize_orientation(candidate.width, candidate.height)
    requested = (request.orientation or "").strip().lower()
    if requested:
        if candidate_orientation == requested:
            score += 1000.0
        else:
            score -= 250.0

    if request.min_width and candidate.width < request.min_width:
        score -= 500.0
    if request.min_height and candidate.height < request.min_height:
        score -= 500.0

    if candidate.license_tier == LICENSE_TIER_NO_ATTRIBUTION:
        score += 250.0

    # Larger images score higher, but only as a tie-breaker; entity accuracy
    # and metadata relevance must dominate pixel count.
    pixel_score = max(candidate.width, 0) * max(candidate.height, 0) / 1000.0
    score += min(pixel_score, 1500.0)
    return score


# ---------------------------------------------------------------------------
# Attribution text
# ---------------------------------------------------------------------------


PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "openverse": "Openverse",
    "wikimedia": "Wikimedia Commons",
    "pexels": "Pexels",
    "pixabay": "Pixabay",
}


def build_attribution_text(filename: str, candidate: AssetCandidate) -> str:
    """Render the canonical attribution string for the manifest.

    Format:
        ``filename — "title" by author, via Provider, license: name (url)``

    Empty fields are gracefully omitted. The text is intended for use by
    the Executor when generating in-SVG credit elements; it is not meant
    to be machine-parsed downstream.
    """
    provider_name = PROVIDER_DISPLAY_NAMES.get(
        candidate.provider, candidate.provider or "unknown"
    )

    parts: list[str] = [filename or candidate.download_url or "image"]
    middle: list[str] = []
    if candidate.title:
        middle.append(f'"{candidate.title}"')
    if candidate.author:
        middle.append(f"by {candidate.author}")
    middle.append(f"via {provider_name}")
    parts.append(" ".join(middle))

    license_part = candidate.license_name or candidate.license_url
    if license_part:
        if candidate.license_url and candidate.license_name:
            license_part = f"{candidate.license_name} ({candidate.license_url})"
        parts.append(f"license: {license_part}")

    return " — ".join(parts)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def ensure_json_parent(path: str | Path) -> Path:
    """Make sure the parent directory of ``path`` exists; return as Path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
