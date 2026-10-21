"""Shared data update coordinator for closed-school polling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SchoolStatus, TvaApiError, async_fetch_closed, status_for_school
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ClosuresData:
    """Snapshot of the TVA closed-schools feed."""

    last_updated: datetime | None
    institutions: dict[int, dict[str, Any]]


class ClosuresCoordinator(DataUpdateCoordinator[ClosuresData]):
    """Poll the TVA closed-schools endpoint once for every configured school."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the shared coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.session = async_get_clientsession(hass)

    async def _async_update_data(self) -> ClosuresData:
        """Fetch the latest closed-school list."""
        try:
            last_updated, institutions = await async_fetch_closed(self.session)
        except TvaApiError as err:
            raise UpdateFailed(str(err)) from err

        _LOGGER.debug(
            "TVA closed-schools update: %s institutions, lastUpdated=%s",
            len(institutions),
            last_updated,
        )
        return ClosuresData(last_updated=last_updated, institutions=institutions)

    def status_for(self, school_id: int) -> SchoolStatus:
        """Resolve the current status of one school."""
        if self.data is None:
            return SchoolStatus(school_id=school_id, closed=False)
        return status_for_school(
            school_id,
            self.data.institutions,
            self.data.last_updated,
            dt_util.now(),
        )


type EcolesFermeesConfigEntry = ConfigEntry[ClosuresCoordinator]


async def async_get_or_create_coordinator(
    hass: HomeAssistant,
) -> ClosuresCoordinator:
    """Return the shared coordinator, creating and refreshing it if needed."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    coordinator: ClosuresCoordinator | None = domain_data.get("coordinator")
    if coordinator is None:
        coordinator = ClosuresCoordinator(hass)
        domain_data["coordinator"] = coordinator
        await coordinator.async_config_entry_first_refresh()
        return coordinator

    if coordinator.data is None:
        await coordinator.async_config_entry_first_refresh()
    return coordinator


async def async_release_coordinator(
    hass: HomeAssistant, unloading_entry: ConfigEntry
) -> None:
    """Shut down the shared coordinator when the last entry unloads."""
    remaining = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.entry_id != unloading_entry.entry_id
        and entry.state is ConfigEntryState.LOADED
    ]
    if remaining:
        return

    domain_data = hass.data.get(DOMAIN)
    if not domain_data:
        return
    coordinator: ClosuresCoordinator | None = domain_data.pop("coordinator", None)
    if coordinator is not None:
        await coordinator.async_shutdown()
