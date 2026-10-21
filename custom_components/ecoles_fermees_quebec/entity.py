"""Shared entity base for Écoles fermées Québec."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SchoolStatus
from .const import CONF_SCHOOL_ID, CONF_SCHOOL_NAME, CONF_TOWN, DOMAIN, TVA_STATUS_URL
from .coordinator import ClosuresCoordinator


class EcolesFermeesEntity(CoordinatorEntity[ClosuresCoordinator]):
    """Base entity attached to one school device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ClosuresCoordinator, entry: ConfigEntry) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._school_id = int(entry.data[CONF_SCHOOL_ID])
        name = entry.data.get(CONF_SCHOOL_NAME, "École")
        town = entry.data.get(CONF_TOWN, "")
        device_name = f"{name} ({town})" if town else str(name)

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._school_id))},
            name=device_name,
            manufacturer="TVA Nouvelles",
            model="École",
            configuration_url=TVA_STATUS_URL,
        )

    @property
    def school_status(self) -> SchoolStatus:
        """Return the latest status for this school."""
        return self.coordinator.status_for(self._school_id)
