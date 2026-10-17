"""Sensor platform for Pylontech FB-L-16 integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Fbl16DataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class Fbl16SensorEntityDescription(SensorEntityDescription):
    """Describes a Pylontech FB-L-16 sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any]
    extra_attributes_fn: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None


# Core Pack & System Sensors
PACK_SENSORS: tuple[Fbl16SensorEntityDescription, ...] = (
    Fbl16SensorEntityDescription(
        key="soc",
        name="State of Charge",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("soc"),
    ),
    Fbl16SensorEntityDescription(
        key="soh",
        name="State of Health",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("soh"),
    ),
    Fbl16SensorEntityDescription(
        key="voltage",
        name="Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda d: d.get("voltage"),
    ),
    Fbl16SensorEntityDescription(
        key="cutoff_voltage",
        name="Cutoff Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda d: d.get("cutoff_voltage"),
    ),
    Fbl16SensorEntityDescription(
        key="current",
        name="Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda d: d.get("current"),
    ),
    Fbl16SensorEntityDescription(
        key="power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda d: d.get("power"),
    ),
    # Inverter Limit Guidance
    Fbl16SensorEntityDescription(
        key="suggested_charge_voltage",
        name="Suggested Charging Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda d: d.get("suggested_charge_voltage"),
    ),
    Fbl16SensorEntityDescription(
        key="suggested_discharge_voltage",
        name="Suggested Discharging Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda d: d.get("suggested_discharge_voltage"),
    ),
    Fbl16SensorEntityDescription(
        key="suggested_charge_current",
        name="Suggested Charging Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda d: d.get("suggested_charge_current"),
    ),
    Fbl16SensorEntityDescription(
        key="suggested_discharge_current",
        name="Suggested Discharging Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda d: d.get("suggested_discharge_current"),
    ),
    Fbl16SensorEntityDescription(
        key="max_charge_current_limit",
        name="Max Charge Current Limit",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda d: d.get("max_charge_current_limit"),
    ),
    Fbl16SensorEntityDescription(
        key="max_discharge_current_limit",
        name="Max Discharge Current Limit",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda d: d.get("max_discharge_current_limit"),
    ),
    # Temperatures
    Fbl16SensorEntityDescription(
        key="ambient_temperature",
        name="Ambient Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("ambient_temperature"),
    ),
    Fbl16SensorEntityDescription(
        key="mos_temperature",
        name="MOS Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("mos_temperature"),
    ),
    # Extremes
    Fbl16SensorEntityDescription(
        key="min_cell_voltage",
        name="Cell Min Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda d: d.get("min_cell_voltage"),
        extra_attributes_fn=lambda d: {"cell_number": d.get("min_cell_voltage_idx")},
    ),
    Fbl16SensorEntityDescription(
        key="max_cell_voltage",
        name="Cell Max Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda d: d.get("max_cell_voltage"),
        extra_attributes_fn=lambda d: {"cell_number": d.get("max_cell_voltage_idx")},
    ),
    Fbl16SensorEntityDescription(
        key="min_cell_temperature",
        name="Cell Min Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("min_cell_temperature"),
        extra_attributes_fn=lambda d: {"cell_number": d.get("min_cell_temperature_idx")},
    ),
    Fbl16SensorEntityDescription(
        key="max_cell_temperature",
        name="Cell Max Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("max_cell_temperature"),
        extra_attributes_fn=lambda d: {"cell_number": d.get("max_cell_temperature_idx")},
    ),
    # Cycle Count & Energy Counters
    Fbl16SensorEntityDescription(
        key="cycles",
        name="Cycles",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("cycles"),
    ),
    Fbl16SensorEntityDescription(
        key="energy_charged_today",
        name="Energy Charged Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_charged_today"),
    ),
    Fbl16SensorEntityDescription(
        key="energy_discharged_today",
        name="Energy Discharged Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_discharged_today"),
    ),
    Fbl16SensorEntityDescription(
        key="energy_charged_total",
        name="Total Energy Charged",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_charged_total"),
    ),
    Fbl16SensorEntityDescription(
        key="energy_discharged_total",
        name="Total Energy Discharged",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_discharged_total"),
    ),
)


# Generate 16 Individual Cell Voltage Entity Descriptions
CELL_VOLTAGE_SENSORS: list[Fbl16SensorEntityDescription] = [
    Fbl16SensorEntityDescription(
        key=f"cell_{i}_voltage",
        name=f"Cell {i} Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=3,
        value_fn=(lambda cell_idx: lambda d: d.get(f"cell_{cell_idx}_voltage"))(i),
    )
    for i in range(1, 17)
]

# Generate 16 Individual Cell Temperature Entity Descriptions
CELL_TEMP_SENSORS: list[Fbl16SensorEntityDescription] = [
    Fbl16SensorEntityDescription(
        key=f"cell_{i}_temperature",
        name=f"Cell {i} Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=(lambda cell_idx: lambda d: d.get(f"cell_{cell_idx}_temperature"))(i),
    )
    for i in range(1, 17)
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pylontech FB-L-16 sensor entities."""
    coordinator: Fbl16DataUpdateCoordinator = entry.runtime_data

    entities: list[Fbl16Sensor] = []

    for desc in PACK_SENSORS:
        entities.append(Fbl16Sensor(coordinator, desc))

    for desc in CELL_VOLTAGE_SENSORS:
        entities.append(Fbl16Sensor(coordinator, desc))

    for desc in CELL_TEMP_SENSORS:
        entities.append(Fbl16Sensor(coordinator, desc))

    async_add_entities(entities)


class Fbl16Sensor(CoordinatorEntity[Fbl16DataUpdateCoordinator], SensorEntity):
    """Representation of a Pylontech FB-L-16 sensor."""

    entity_description: Fbl16SensorEntityDescription

    def __init__(
        self,
        coordinator: Fbl16DataUpdateCoordinator,
        description: Fbl16SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

        # Dynamic Device Info
        dev_model = coordinator.data.get("device_model", "FB-L-16") if coordinator.data else "FB-L-16"
        dev_mfg = coordinator.data.get("manufacturer", "Pylontech") if coordinator.data else "Pylontech"
        dev_sn = coordinator.data.get("system_sn") if coordinator.data else None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=f"{coordinator.name}",
            manufacturer=dev_mfg,
            model=dev_model,
            serial_number=dev_sn,
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes if configured."""
        if not self.coordinator.data or not self.entity_description.extra_attributes_fn:
            return None
        return self.entity_description.extra_attributes_fn(self.coordinator.data)
