"""Sensors for school closures."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import EcolesFermeesConfigEntry
from .api import SchoolStatus
from .const import STATE_CLOSED, STATE_NONE, STATE_OPEN
from .coordinator import ClosuresCoordinator
from .entity import EcolesFermeesEntity


@dataclass(frozen=True, kw_only=True)
class SchoolSensorEntityDescription(SensorEntityDescription):
    """Describes a school sensor."""

    value_fn: Callable[[SchoolStatus], StateType | datetime]


SENSORS: tuple[SchoolSensorEntityDescription, ...] = (
    SchoolSensorEntityDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=[STATE_OPEN, STATE_CLOSED],
        value_fn=lambda status: STATE_CLOSED if status.closed else STATE_OPEN,
    ),
    SchoolSensorEntityDescription(
        key="message",
        translation_key="message",
        value_fn=lambda status: status.message or STATE_NONE,
    ),
    SchoolSensorEntityDescription(
        key="informations",
        translation_key="informations",
        value_fn=lambda status: ", ".join(status.informations) or STATE_NONE,
    ),
    SchoolSensorEntityDescription(
        key="last_updated",
        translation_key="last_updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda status: status.last_updated,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcolesFermeesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors for one school."""
    coordinator = entry.runtime_data
    async_add_entities(
        SchoolSensor(coordinator, entry, description) for description in SENSORS
    )


class SchoolSensor(EcolesFermeesEntity, SensorEntity):
    """Sensor exposing one piece of a school's closure status."""

    entity_description: SchoolSensorEntityDescription

    def __init__(
        self,
        coordinator: ClosuresCoordinator,
        entry: EcolesFermeesConfigEntry,
        description: SchoolSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{self._school_id}_{description.key}"

    @property
    def native_value(self) -> StateType | datetime:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.school_status)
