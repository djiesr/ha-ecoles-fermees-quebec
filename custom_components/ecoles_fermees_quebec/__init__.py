"""Écoles fermées Québec integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import (
    EcolesFermeesConfigEntry,
    async_get_or_create_coordinator,
    async_release_coordinator,
)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: EcolesFermeesConfigEntry) -> bool:
    """Set up one school from a config entry."""
    coordinator = await async_get_or_create_coordinator(hass)
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EcolesFermeesConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await async_release_coordinator(hass, entry)
    return unload_ok
