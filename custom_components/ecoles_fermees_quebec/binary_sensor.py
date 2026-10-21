"""Binary sensors for school closures."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ClosuresCoordinator, EcolesFermeesConfigEntry
from .const import (
    ATTR_CSS,
    ATTR_END,
    ATTR_INFORMATIONS,
    ATTR_LAST_UPDATED,
    ATTR_MESSAGE,
    ATTR_SCHOOL_ID,
    ATTR_START,
    ATTR_TOWN,
    CONF_TOWN,
)
from .entity import EcolesFermeesEntity

CLOSED_DESCRIPTION = BinarySensorEntityDescription(
    key="closed",
    translation_key="closed",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcolesFermeesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors for one school."""
    async_add_entities([SchoolClosedBinarySensor(entry.runtime_data, entry)])


class SchoolClosedBinarySensor(EcolesFermeesEntity, BinarySensorEntity):
    """On when the school is currently closed."""

    entity_description = CLOSED_DESCRIPTION

    def __init__(
        self, coordinator: ClosuresCoordinator, entry: EcolesFermeesConfigEntry
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self._school_id}_closed"

    @property
    def is_on(self) -> bool:
        """Return True if the school is closed."""
        return self.school_status.closed

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return extra attributes useful for automations."""
        status = self.school_status
        return {
            ATTR_SCHOOL_ID: self._school_id,
            ATTR_TOWN: status.town or self._entry.data.get(CONF_TOWN),
            ATTR_CSS: status.css_name,
            ATTR_MESSAGE: status.message,
            ATTR_INFORMATIONS: status.informations,
            ATTR_START: status.start.isoformat() if status.start else None,
            ATTR_END: status.end.isoformat() if status.end else None,
            ATTR_LAST_UPDATED: (
                status.last_updated.isoformat() if status.last_updated else None
            ),
        }
