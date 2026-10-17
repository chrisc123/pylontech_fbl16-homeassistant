"""Config flow for Pylontech FB-L-16 integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_DEVICE_KEY, CONF_PRODUCT_KEY, DOMAIN, QUEC_MFG_ID
from .quectel_codec import extract_quec_info_from_manufacturer_data, parse_quec_manufacturer_bytes

_LOGGER = logging.getLogger(__name__)


class Fbl16ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pylontech FB-L-16."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device_key: str = ""
        self._discovered_product_key: str = ""

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle discovery via Bluetooth advertisements."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        # Extract Quectel Manufacturer Data using the split-key extractor
        adv_info = extract_quec_info_from_manufacturer_data(discovery_info.manufacturer_data)
        if adv_info:
            self._discovered_device_key = adv_info.dk
            self._discovered_product_key = adv_info.pk

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery of a Pylontech battery."""
        assert self._discovery_info is not None

        if user_input is not None:
            dk = user_input.get(CONF_DEVICE_KEY, self._discovered_device_key).strip().upper()
            return self.async_create_entry(
                title=self._discovery_info.name or f"FB-L-16 ({self._discovery_info.address})",
                data={
                    CONF_ADDRESS: self._discovery_info.address,
                    CONF_DEVICE_KEY: dk,
                    CONF_PRODUCT_KEY: self._discovered_product_key,
                },
            )

        name = self._discovery_info.name or self._discovery_info.address
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": name},
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_KEY,
                        default=self._discovered_device_key,
                    ): str,
                }
            ),
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual user addition of a Pylontech battery."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"FB-L-16 ({address})",
                data={
                    CONF_ADDRESS: address,
                    CONF_DEVICE_KEY: user_input[CONF_DEVICE_KEY].strip().upper(),
                    CONF_PRODUCT_KEY: user_input.get(CONF_PRODUCT_KEY, ""),
                },
            )

        # Pre-populate discovered devices if available
        discovered_addresses: list[str] = []
        for info in async_discovered_service_info(self.hass):
            if (info.name or "").startswith(("PY_FBL16_", "PY_Fidus_", "PY_UF5000_", "PY_")):
                discovered_addresses.append(info.address)

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(discovered_addresses) if discovered_addresses else str,
                vol.Required(CONF_DEVICE_KEY): str,
                vol.Optional(CONF_PRODUCT_KEY, default=""): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
