"""Client and helpers for the unofficial TVA school-closure API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import unicodedata
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp

from .const import (
    DEFAULT_HEADERS,
    REQUEST_TIMEOUT,
    URL_CLOSED,
    URL_LIST,
)

_LOGGER = logging.getLogger(__name__)
QUEBEC_TZ = ZoneInfo("America/Toronto")


class TvaApiError(Exception):
    """Raised when the TVA API cannot be reached or parsed."""


@dataclass(frozen=True, slots=True)
class School:
    """A school from the TVA directory."""

    school_id: int
    name: str
    town: str

    @property
    def label(self) -> str:
        """Human-readable label used in the config flow."""
        return f"{self.name} ({self.town})"


@dataclass(slots=True)
class SchoolStatus:
    """Resolved open/closed status for one school."""

    school_id: int
    closed: bool
    message: str | None = None
    informations: list[str] = field(default_factory=list)
    start: datetime | None = None
    end: datetime | None = None
    last_updated: datetime | None = None
    css_name: str | None = None
    institution_type: str | None = None
    name: str | None = None
    town: str | None = None


def normalize_text(value: str) -> str:
    """Lowercase a string and strip accents for search matching."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def parse_tva_datetime(value: str | None) -> datetime | None:
    """Parse TVA timestamps (ISO-8601 or dd-mm-YYYY HH:MM:SS)."""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        parsed = None

    if parsed is None:
        for fmt in ("%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=QUEBEC_TZ)
    return parsed


def _named_value(value: Any) -> str | None:
    if isinstance(value, dict):
        name = value.get("name")
        return str(name) if name else None
    return None


def status_for_school(
    school_id: int,
    institutions: dict[int, dict[str, Any]],
    last_updated: datetime | None,
    now: datetime,
) -> SchoolStatus:
    """Return the current status of a school from the closed-schools payload."""
    institution = institutions.get(school_id)
    if institution is None:
        return SchoolStatus(school_id=school_id, closed=False, last_updated=last_updated)

    now = _ensure_aware(now)
    closures = institution.get("closures") or []
    closure = _active_closure(closures, now)
    closed = closure is not None or not closures

    message = None
    informations: list[str] = []
    start = None
    end = None
    if closure:
        raw_message = closure.get("message")
        message = str(raw_message).strip() if raw_message else None
        informations = [
            str(item["name"])
            for item in closure.get("closure_informations") or []
            if isinstance(item, dict) and item.get("name")
        ]
        start = parse_tva_datetime(closure.get("datetime_start"))
        end = parse_tva_datetime(closure.get("datetime_end"))

    parent = institution.get("parent") or {}
    return SchoolStatus(
        school_id=school_id,
        closed=closed,
        message=message,
        informations=informations,
        start=start,
        end=end,
        last_updated=last_updated,
        css_name=_named_value(parent) if isinstance(parent, dict) else None,
        institution_type=_named_value(institution.get("institution_type")),
        name=institution.get("name"),
        town=institution.get("town"),
    )


def _active_closure(closures: list[Any], now: datetime) -> dict[str, Any] | None:
    """Pick the closure that applies right now, if any."""
    dated_active: list[dict[str, Any]] = []
    undated: list[dict[str, Any]] = []

    for raw in closures:
        if not isinstance(raw, dict):
            continue
        start = parse_tva_datetime(raw.get("datetime_start"))
        end = parse_tva_datetime(raw.get("datetime_end"))
        if start is None and end is None:
            undated.append(raw)
            continue
        window_start = start or datetime.min.replace(tzinfo=timezone.utc)
        window_end = end or datetime.max.replace(tzinfo=timezone.utc)
        if window_start <= now <= window_end:
            dated_active.append(raw)

    if dated_active:
        return dated_active[-1]
    if undated:
        return undated[-1]
    # Historical-only dump: treat as open.
    return None


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def parse_institutions(payload: dict[str, Any]) -> tuple[datetime | None, dict[int, dict[str, Any]]]:
    """Extract lastUpdated and a map of institutions keyed by id."""
    last_updated = parse_tva_datetime(payload.get("lastUpdated"))
    result = payload.get("result") or {}
    institutions: dict[int, dict[str, Any]] = {}
    for item in result.get("institutions") or []:
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        try:
            institutions[int(item["id"])] = item
        except (TypeError, ValueError):
            continue
    return last_updated, institutions


def parse_school_list(payload: dict[str, Any]) -> list[School]:
    """Parse the TVA school directory."""
    result = payload.get("result") or {}
    schools: list[School] = []
    for item in result.get("institutions") or []:
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        try:
            school_id = int(item["id"])
        except (TypeError, ValueError):
            continue
        name = str(item.get("name") or "").strip()
        town = str(item.get("town") or "").strip()
        if not name:
            continue
        schools.append(School(school_id=school_id, name=name, town=town))
    return schools


def search_schools(schools: list[School], query: str) -> list[School]:
    """Filter schools by name or town (accent-insensitive)."""
    needle = normalize_text(query.strip())
    if not needle:
        return []
    return [
        school
        for school in schools
        if needle in normalize_text(school.name) or needle in normalize_text(school.town)
    ]


async def async_fetch_json(session: aiohttp.ClientSession, url: str) -> dict[str, Any]:
    """GET a JSON document from the TVA API."""
    try:
        async with session.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
        ) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
    except TimeoutError as err:
        raise TvaApiError("Timeout while contacting the TVA API") from err
    except aiohttp.ClientError as err:
        raise TvaApiError(f"Cannot reach the TVA API: {err}") from err
    except ValueError as err:
        raise TvaApiError("Invalid JSON from the TVA API") from err

    if not isinstance(payload, dict):
        raise TvaApiError("Unexpected TVA API payload")
    if payload.get("success") is False:
        raise TvaApiError("TVA API returned success=false")
    return payload


async def async_fetch_closed(
    session: aiohttp.ClientSession,
) -> tuple[datetime | None, dict[int, dict[str, Any]]]:
    """Fetch currently closed schools."""
    payload = await async_fetch_json(session, URL_CLOSED)
    return parse_institutions(payload)


async def async_fetch_schools(session: aiohttp.ClientSession) -> list[School]:
    """Fetch the school directory."""
    payload = await async_fetch_json(session, URL_LIST)
    schools = parse_school_list(payload)
    _LOGGER.debug("Loaded %s schools from TVA", len(schools))
    return schools
