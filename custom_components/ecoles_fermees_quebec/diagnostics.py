"""Diagnostics for Écoles fermées Québec."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import EcolesFermeesConfigEntry
from .const import CONF_SCHOOL_ID, CONF_SCHOOL_NAME, CONF_TOWN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EcolesFermeesConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    school_id = int(entry.data[CONF_SCHOOL_ID])
    status = coordinator.status_for(school_id)
    return {
        "entry": {
            "school_id": school_id,
            "school_name": entry.data.get(CONF_SCHOOL_NAME),
            "town": entry.data.get(CONF_TOWN),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                str(coordinator.last_exception) if coordinator.last_exception else None
            ),
            "closed_count": (
                len(coordinator.data.institutions) if coordinator.data else 0
            ),
        },
        "status": {
            "closed": status.closed,
            "message": status.message,
            "informations": status.informations,
            "start": status.start.isoformat() if status.start else None,
            "end": status.end.isoformat() if status.end else None,
            "last_updated": (
                status.last_updated.isoformat() if status.last_updated else None
            ),
            "css_name": status.css_name,
            "institution_type": status.institution_type,
        },
    }
