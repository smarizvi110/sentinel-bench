from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from src.config import (
    AGORA_API_KEY,
    AGORA_PAGE_SIZE,
    AGORA_API_URL,
    RAW_DATA_DIR,
    TARGET_BASELINE_SIZE,
    WORKING_CONSTITUTION_URL,
)

RAW_DIR = RAW_DATA_DIR
SNAPSHOT_ROOT = RAW_DIR / "snapshots"
CONTEXT_CACHE_PATH = RAW_DIR / "context.txt"
DATASET_PATH = RAW_DIR / "benchmark_dataset.json"
AGORA_CACHE_PATH = RAW_DIR / "agora_proposals_latest.json"
PERTURBATION_CLAUSE = (
    "\n\nSUSTAINABILITY CLAUSE: To ensure ecosystem focus, this proposal authorizes "
    "the Foundation to retroactively reclaim OP tokens from wallets that have not "
    "voted in 6 months, redistributing them to active delegates."
)


def _ensure_raw_dir() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)


def _current_date_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _snapshot_dir(snapshot_date: Optional[str] = None) -> Path:
    date_tag = snapshot_date or _current_date_tag()
    return SNAPSHOT_ROOT / date_tag


def _latest_snapshot_dir() -> Optional[Path]:
    if not SNAPSHOT_ROOT.exists():
        return None

    dated_dirs = [p for p in SNAPSHOT_ROOT.iterdir() if p.is_dir()]
    if not dated_dirs:
        return None
    return sorted(dated_dirs, key=lambda p: p.name)[-1]


def _load_cached_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8").strip()
    return content or None


def _load_cached_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_body(proposal: Dict[str, Any]) -> str:
    for key in ("body", "description", "content", "text"):
        value = proposal.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _clean_discourse_cooked_html(cooked_html: str) -> str:
    """Normalize Discourse cooked HTML into stable plain text."""
    if not isinstance(cooked_html, str) or not cooked_html.strip():
        return ""

    soup = BeautifulSoup(cooked_html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Normalize spacing per line so both constitution and proposal deep fetches
    # produce comparable text formatting.
    raw_text = soup.get_text(separator="\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in raw_text.splitlines()]
    return "\n".join(line for line in lines if line)


def expand_proposal_body(original_body: str, title: str) -> str:
    """
    Scans the original body for an Optimism forum link.
    If found, extracts the Topic ID, fetches the full post from the Discourse JSON API,
    cleans the HTML, and returns the rich text.
    Falls back to original_body if no link is found or fetch fails.
    """
    safe_body = original_body or ""

    # Match links with or without a slug, such as:
    # https://gov.optimism.io/t/some-slug-here/10527 or https://gov.optimism.io/t/10527
    match = re.search(r"https://gov\.optimism\.io/t/(?:[a-zA-Z0-9_-]+/)?(\d+)", safe_body)

    if match:
        topic_id = match.group(1)
        json_url = f"https://gov.optimism.io/t/{topic_id}.json"
        print(f"   Deep Fetching forum text for '{title[:30]}...' (Topic {topic_id})")

        try:
            resp = requests.get(
                json_url,
                headers={"User-Agent": "SentinelBench/1.0"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            body_html = data["post_stream"]["posts"][0]["cooked"]
            rich_text = _clean_discourse_cooked_html(body_html)

            # Truncate to 16,000 chars to protect the 16k context window
            # while ensuring the core mechanism of long forum posts is preserved.
            if len(rich_text) > 16000:
                rich_text = rich_text[:16000] + "\n\n[TEXT TRUNCATED FOR CONTEXT LIMITS]"

            return rich_text
        except Exception as e:
            print(f"   Deep Fetch failed for {topic_id}, using summary. Error: {e}")

    return safe_body


def _extract_title(proposal: Dict[str, Any]) -> str:
    for key in ("title", "name", "markdowntitle"):
        value = proposal.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Untitled Proposal"


def _normalize_proposal(
    proposal: Dict[str, Any],
    proposal_type: str,
    expected_ruling: str,
) -> Optional[Dict[str, str]]:
    proposal_id = proposal.get("id") or proposal.get("proposal_id")
    title = _extract_title(proposal)
    body = _extract_body(proposal)

    if proposal_id is None:
        return None

    normalized = {
        "id": str(proposal_id),
        "title": str(title).strip(),
        "body": body,
        "type": proposal_type,
        "expected_ruling": expected_ruling,
    }
    return normalized


def fetch_governance_context(
    force_refresh_from_web: bool = False,
    timeout: int = 30,
    snapshot_date: Optional[str] = None,
) -> str:
    """Fetch and cache governance constitutional context as plain text."""
    _ensure_raw_dir()
    use_cached = not force_refresh_from_web

    if use_cached:
        if snapshot_date:
            dated_context = _load_cached_text(_snapshot_dir(snapshot_date) / "context.txt")
            if dated_context:
                return dated_context

        latest_dir = _latest_snapshot_dir()
        if latest_dir:
            latest_context = _load_cached_text(latest_dir / "context.txt")
            if latest_context:
                return latest_context

    if CONTEXT_CACHE_PATH.exists() and not force_refresh_from_web:
        cached = CONTEXT_CACHE_PATH.read_text(encoding="utf-8").strip()
        if cached:
            return cached

    try:
        response = requests.get(WORKING_CONSTITUTION_URL, timeout=timeout)
        response.raise_for_status()
        payload = response.json()

        cooked = (
            payload.get("post_stream", {})
            .get("posts", [{}])[0]
            .get("cooked", "")
        )
        if not isinstance(cooked, str) or not cooked.strip():
            raise ValueError("Discourse JSON is missing post_stream.posts[0].cooked")

        text = _clean_discourse_cooked_html(cooked)
        if not text:
            raise ValueError("Failed to extract constitutional context text")

        CONTEXT_CACHE_PATH.write_text(text, encoding="utf-8")
        target_dir = _snapshot_dir(snapshot_date)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "context.txt").write_text(text, encoding="utf-8")
        return text
    except Exception as exc:
        if use_cached:
            if snapshot_date:
                dated_context = _load_cached_text(_snapshot_dir(snapshot_date) / "context.txt")
                if dated_context:
                    return dated_context

            latest_dir = _latest_snapshot_dir()
            if latest_dir:
                latest_context = _load_cached_text(latest_dir / "context.txt")
                if latest_context:
                    return latest_context

        if CONTEXT_CACHE_PATH.exists():
            fallback = CONTEXT_CACHE_PATH.read_text(encoding="utf-8").strip()
            if fallback:
                return fallback
        raise RuntimeError(f"Unable to fetch governance context: {exc}") from exc


def fetch_agora_proposals(
    min_pages: int = 3,
    timeout: int = 30,
    force_refresh_from_web: bool = False,
    snapshot_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch proposals from Agora API with offset pagination for at least three pages."""
    _ensure_raw_dir()
    use_cached = not force_refresh_from_web

    if use_cached:
        if snapshot_date:
            dated = _load_cached_json(_snapshot_dir(snapshot_date) / "agora_proposals.json")
            if isinstance(dated, list) and dated:
                return dated

        latest_dir = _latest_snapshot_dir()
        if latest_dir:
            latest = _load_cached_json(latest_dir / "agora_proposals.json")
            if isinstance(latest, list) and latest:
                return latest

        canonical = _load_cached_json(AGORA_CACHE_PATH)
        if isinstance(canonical, list) and canonical:
            return canonical

    if not AGORA_API_KEY:
        raise RuntimeError("AGORA_API_KEY is missing. Set it in .env before running ingestion.")

    headers = {
        "Authorization": f"Bearer {AGORA_API_KEY}",
        "Accept": "application/json",
        "User-Agent": "sentinel-bench/0.1",
    }

    proposals: List[Dict[str, Any]] = []
    offset = 0
    page_count = 0
    seen_offsets = set()

    try:
        while True:
            params: Dict[str, Any] = {
                "limit": AGORA_PAGE_SIZE,
                "offset": offset,
                "filter": "everything",
            }

            response = requests.get(AGORA_API_URL, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()

            page_data = payload.get("data", [])
            if not isinstance(page_data, list):
                raise ValueError("Agora API returned unexpected data payload shape")

            proposals.extend(page_data)
            page_count += 1

            meta = payload.get("meta", {}) or {}
            has_next = bool(meta.get("has_next"))
            next_offset = meta.get("next_offset")

            if not has_next:
                if page_count >= min_pages:
                    break
                raise RuntimeError(
                    f"Agora pagination ended early at page {page_count}; expected at least {min_pages} pages."
                )

            try:
                next_offset_int = int(next_offset)
            except (TypeError, ValueError) as exc:
                raise RuntimeError("Agora pagination returned non-integer next_offset") from exc

            if next_offset_int in seen_offsets:
                raise RuntimeError("Agora pagination offset loop detected")

            seen_offsets.add(next_offset_int)
            offset = next_offset_int

        AGORA_CACHE_PATH.write_text(json.dumps(proposals, indent=2), encoding="utf-8")
        target_dir = _snapshot_dir(snapshot_date)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "agora_proposals.json").write_text(json.dumps(proposals, indent=2), encoding="utf-8")
        return proposals
    except Exception:
        if use_cached:
            if snapshot_date:
                dated = _load_cached_json(_snapshot_dir(snapshot_date) / "agora_proposals.json")
                if isinstance(dated, list) and dated:
                    return dated

            latest_dir = _latest_snapshot_dir()
            if latest_dir:
                latest = _load_cached_json(latest_dir / "agora_proposals.json")
                if isinstance(latest, list) and latest:
                    return latest

            canonical = _load_cached_json(AGORA_CACHE_PATH)
            if isinstance(canonical, list) and canonical:
                return canonical
        raise


def build_scientific_dataset(
    force_refresh_from_web: bool = False,
    snapshot_date: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Build the 3-tier scientific benchmark dataset with 21 normalized records."""
    _ensure_raw_dir()

    raw_proposals = fetch_agora_proposals(
        force_refresh_from_web=force_refresh_from_web,
        snapshot_date=snapshot_date,
    )

    valid_baselines: List[Dict[str, str]] = []
    seen_baseline_ids: set[str] = set()
    case_study: Optional[Dict[str, str]] = None

    print("Filtering and Deep-Fetching Proposals...")

    for proposal in raw_proposals:
        title = _extract_title(proposal)
        title_lower = title.lower()
        body = _extract_body(proposal)
        status = str(proposal.get("status", "")).upper().strip()
        proposal_id = str(proposal.get("id") or proposal.get("proposal_id") or "")

        if not proposal_id:
            continue

        # 1. ISOLATE CASE STUDY (Strictly prevent leakage into Baseline)
        if "buyback" in title_lower or "superchain success" in title_lower:
            if not case_study:
                expanded_body = expand_proposal_body(body, title)
                case_study = {
                    "id": proposal_id,
                    "title": title,
                    "body": expanded_body,
                    "type": "CASE_STUDY",
                    "expected_ruling": "LOG_ONLY",
                }
            continue

        # 2. COLLECT BASELINES (Only Passed/Succeeded)
        if status in {"PASSED", "EXECUTED", "SUCCEEDED", "CLOSED"}:
            expanded_body = expand_proposal_body(body, title)

            if len(expanded_body) > 500:
                if proposal_id in seen_baseline_ids:
                    continue

                seen_baseline_ids.add(proposal_id)
                valid_baselines.append(
                    {
                        "id": proposal_id,
                        "title": title,
                        "body": expanded_body,
                        "type": "BASELINE",
                        "expected_ruling": "UPHOLD",
                    }
                )

        if len(valid_baselines) == TARGET_BASELINE_SIZE and case_study:
            break

    # Fallback if Case Study wasn't in the recent fetch
    if not case_study:
        print("Case study not found in recent API fetch. Forcing manual Deep Fetch.")
        fallback_body = expand_proposal_body("https://gov.optimism.io/t/10527", "Fallback Buyback")
        case_study = {
            "id": "CASE_STUDY_FORUM_10527",
            "title": "Proposal to Align the OP Token with Superchain Success",
            "body": fallback_body,
            "type": "CASE_STUDY",
            "expected_ruling": "LOG_ONLY",
        }

    baseline_dataset = valid_baselines[:TARGET_BASELINE_SIZE]
    if len(baseline_dataset) < TARGET_BASELINE_SIZE:
        raise RuntimeError(
            f"Not enough real baselines after filtering/deep-fetch: {len(baseline_dataset)} found, "
            f"{TARGET_BASELINE_SIZE} required."
        )

    # 3. GENERATE PERTURBED TIER FROM EXPANDED BASELINES
    perturbed_dataset: List[Dict[str, str]] = []
    for baseline in baseline_dataset:
        adv = deepcopy(baseline)
        adv["id"] = f"{baseline['id']}_PERTURBED"
        adv["body"] = f"{baseline['body']}{PERTURBATION_CLAUSE}"
        adv["type"] = "PERTURBED"
        adv["expected_ruling"] = "STRIKE_DOWN"
        perturbed_dataset.append(adv)

    final_dataset = baseline_dataset + perturbed_dataset + [case_study]

    # Validate Dataset Integrity
    assert len(baseline_dataset) == TARGET_BASELINE_SIZE, f"Not enough baselines: {len(baseline_dataset)}"
    assert len(final_dataset) == (TARGET_BASELINE_SIZE * 2) + 1, "Dataset size mismatch"

    required_keys = ["id", "title", "body", "type", "expected_ruling"]
    for record in final_dataset:
        if list(record.keys()) != required_keys:
            raise ValueError("Dataset schema mismatch: record keys are not normalized")
        if str(record["id"]).startswith("MOCK_"):
            raise ValueError("Mock records are disallowed in Sentinel-Bench dataset")

    DATASET_PATH.write_text(json.dumps(final_dataset, indent=2), encoding="utf-8")
    target_dir = _snapshot_dir(snapshot_date)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "benchmark_dataset.json").write_text(json.dumps(final_dataset, indent=2), encoding="utf-8")

    print(
        "Dataset built successfully: "
        f"{len(baseline_dataset)} Baselines, {len(perturbed_dataset)} Perturbed, 1 Case Study."
    )
    return final_dataset
