"""Binary sensor platform for Pylontech FB-L-16 integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Fbl16DataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class Fbl16BinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Pylontech FB-L-16 binary sensor entity."""

    is_on_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSORS: tuple[Fbl16BinarySensorEntityDescription, ...] = (
    Fbl16BinarySensorEntityDescription(
        key="problem",
        name="Problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda d: d.get("system_state") in (2, 3),
    ),
    Fbl16BinarySensorEntityDescription(
        key="heater",
        name="Heater",
        device_class=BinarySensorDeviceClass.HEAT,
        is_on_fn=lambda d: bool(d.get("heater_state") == 1),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pylontech FB-L-16 binary sensor entities from a config entry."""
    coordinator: Fbl16DataUpdateCoordinator = entry.runtime_data

    entities = [
        Fbl16BinarySensor(
            coordinator=coordinator,
            description=description,
            entry=entry,
        )
        for description in BINARY_SENSORS
    ]
    async_add_entities(entities)


class Fbl16BinarySensor(CoordinatorEntity[Fbl16DataUpdateCoordinator], BinarySensorEntity):
    """Representation of a Pylontech FB-L-16 binary sensor."""

    entity_description: Fbl16BinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Fbl16DataUpdateCoordinator,
        description: Fbl16BinarySensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=f"Pylontech FB-L-16 ({coordinator.address})",
            manufacturer="Pylontech",
            model="FB-L-16",
        )

    @property
    def available(self) -> bool:
        """Return True if entity has valid data and is not stale."""
        return bool(self.coordinator.data) and not self.coordinator.is_stale and super().available

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None
        return self.entity_description.is_on_fn(self.coordinator.data)
