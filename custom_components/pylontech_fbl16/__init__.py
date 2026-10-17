"""The Pylontech FB-L-16 Battery integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_KEY, DOMAIN
from .coordinator import Fbl16DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pylontech FB-L-16 from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    device_key: str = entry.data[CONF_DEVICE_KEY]

    coordinator = Fbl16DataUpdateCoordinator(
        hass=hass,
        address=address,
        device_key=device_key,
        name=entry.title,
    )

    # Store coordinator on runtime_data (modern HA standard)
    entry.runtime_data = coordinator

    # Start persistent BLE telemetry stream task in background
    await coordinator.async_start_streaming()

    # Forward setup to sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: Fbl16DataUpdateCoordinator = entry.runtime_data

    # Stop background streaming task and disconnect BLE client cleanly
    await coordinator.async_stop_streaming()

    # Unload platforms
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
