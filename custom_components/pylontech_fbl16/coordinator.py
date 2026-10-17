"""Coordinator for Pylontech FB-L-16 battery telemetry over BLE."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import struct
from typing import Any

from bleak import BleakClient
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CMD_CHALLENGE_REQ,
    CMD_LOGIN_REQ,
    CMD_TELEMETRY_STREAM,
    DOMAIN,
    FIELD_AMBIENT_TEMP,
    FIELD_CELL_TEMP_MAX,
    FIELD_CELL_TEMP_MAX_IDX,
    FIELD_CELL_TEMP_MIN,
    FIELD_CELL_TEMP_MIN_IDX,
    FIELD_CELL_TEMPS_BYTES,
    FIELD_CELL_VOLTAGE_MAX,
    FIELD_CELL_VOLTAGE_MAX_IDX,
    FIELD_CELL_VOLTAGE_MIN,
    FIELD_CELL_VOLTAGE_MIN_IDX,
    FIELD_CELL_VOLTAGES_BYTES,
    FIELD_CUTOFF_VOLTAGE,
    FIELD_DEVICE_MODEL,
    FIELD_ENERGY_CHG_TODAY,
    FIELD_ENERGY_CHG_TOTAL,
    FIELD_ENERGY_DISCHG_TODAY,
    FIELD_ENERGY_DISCHG_TOTAL,
    FIELD_MANUFACTURER,
    FIELD_MAX_CHG_CURRENT_LIMIT,
    FIELD_MAX_DISCHG_CURRENT_LIMIT,
    FIELD_MAX_TARGET_SOC,
    FIELD_MODULE_SN,
    FIELD_MOS_TEMP,
    FIELD_ONLINE_MODULES,
    FIELD_PACK_CURRENT,
    FIELD_PACK_VOLTAGE,
    FIELD_RATED_CAPACITY_AH,
    FIELD_SOC,
    FIELD_SOH,
    FIELD_SUGGESTED_CHG_I,
    FIELD_SUGGESTED_CHG_V,
    FIELD_SUGGESTED_DISCHG_I,
    FIELD_SUGGESTED_DISCHG_V,
    FIELD_SYSTEM_SN,
    FIELD_TOTAL_CELLS,
    FIELD_TOTAL_CYCLES,
    FIELD_TOTAL_MODULES,
    QUEC_CHAR_UUID,
)
from .quectel_codec import (
    QuectelFrameStreamParser,
    build_quec_frame,
    decode_ttlv_payload,
    derive_quectel_session,
    encode_ttlv_binary,
)

_LOGGER = logging.getLogger(__name__)


class Fbl16DataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinates BLE connection, Quectel handshake, and live telemetry streaming."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        device_key: str,
        name: str = "Pylontech FB-L-16",
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=90),
        )
        self.address = address
        self.device_key = device_key
        self._client: BleakClient | None = None
        self._parser = QuectelFrameStreamParser()
        self._ttlv_queue: asyncio.Queue[tuple[int, int, dict[int, Any]]] = asyncio.Queue()
        self._stream_task: asyncio.Task | None = None
        self._packet_id = 1
        self._shutdown = False
        self._lock = asyncio.Lock()

    def _next_packet_id(self) -> int:
        pid = self._packet_id
        self._packet_id = 1 if self._packet_id >= 65534 else (self._packet_id + 1)
        return pid

    async def async_start_streaming(self) -> None:
        """Starts the persistent background BLE streaming task."""
        if self._stream_task is None or self._stream_task.done():
            self._shutdown = False
            self._stream_task = self.hass.async_create_background_task(
                self._run_streaming_loop(), f"{DOMAIN}_{self.address}_stream"
            )

    async def async_stop_streaming(self) -> None:
        """Stops the streaming loop and cleans up BLE connection."""
        self._shutdown = True
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None
        await self._disconnect_client()

    async def _disconnect_client(self) -> None:
        if self._client:
            try:
                if self._client.is_connected:
                    await self._client.disconnect()
            except Exception as exc:
                _LOGGER.debug("Error disconnecting BleakClient: %s", exc)
            finally:
                self._client = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Called periodically by Home Assistant; ensures streaming task is alive."""
        if not self._shutdown and (self._stream_task is None or self._stream_task.done()):
            await self.async_start_streaming()
        return self.data or {}

    async def _run_streaming_loop(self) -> None:
        """Main loop that connects, authenticates, and streams live telemetry frames."""
        retry_delay = 5.0

        while not self._shutdown:
            try:
                ble_device = bluetooth.async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )
                if ble_device is None:
                    _LOGGER.debug("Battery %s not in range yet; waiting for advertisement...", self.address)
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(60.0, retry_delay * 1.5)
                    continue

                _LOGGER.info("Connecting to Pylontech FB-L-16 (%s)...", self.address)
                async with self._lock:
                    self._parser = QuectelFrameStreamParser()
                    while not self._ttlv_queue.empty():
                        self._ttlv_queue.get_nowait()

                    self._client = await establish_connection(
                        client_class=BleakClient,
                        device=ble_device,
                        name=f"{self.name} ({self.address})",
                        disconnected_callback=self._on_disconnected,
                        max_attempts=4,
                        use_services_cache=True,
                        ble_device_callback=lambda: bluetooth.async_ble_device_from_address(
                            self.hass, self.address, connectable=True
                        ),
                    )

                    await self._client.start_notify(QUEC_CHAR_UUID, self._on_ble_notification)
                    await self._perform_handshake()
                    retry_delay = 5.0  # Reset backoff on successful handshake
                    _LOGGER.info("Authentication complete. Listening for telemetry broadcast...")

                # Wait for connection to drop or shutdown
                while self._client and self._client.is_connected and not self._shutdown:
                    await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.warning("Connection to %s failed: %s; retrying in %.1fs...", self.address, err, retry_delay)
                await self._disconnect_client()
                await asyncio.sleep(retry_delay)
                retry_delay = min(60.0, retry_delay * 1.5)

    def _on_disconnected(self, _client: BleakClient) -> None:
        """Callback when the underlying BLE connection disconnects."""
        _LOGGER.info("Battery %s disconnected. Stream loop will reconnect automatically.", self.address)

    def _on_ble_notification(self, _sender: Any, data: bytearray) -> None:
        """Notification handler for characteristic 0x9C40."""
        for pid, cmd, payload in self._parser.feed(bytes(data)):
            if cmd == CMD_TELEMETRY_STREAM:
                ttlv = decode_ttlv_payload(payload)
                # Primary telemetry is packed in Struct 33 / Struct 0
                if 33 in ttlv and isinstance(ttlv[33], dict) and 0 in ttlv[33]:
                    self._process_telemetry_dict(ttlv[33][0])
            else:
                ttlv = decode_ttlv_payload(payload)
                self._ttlv_queue.put_nowait((pid, cmd, ttlv))

    async def _perform_handshake(self) -> None:
        """Performs Quectel 2-step challenge-response authentication."""
        req1 = build_quec_frame(CMD_CHALLENGE_REQ, b"", packet_id=self._next_packet_id())
        await self._client.write_gatt_char(QUEC_CHAR_UUID, req1, response=False)

        _pid, _cmd, ttlv1 = await asyncio.wait_for(self._ttlv_queue.get(), timeout=10.0)
        random_val = ttlv1.get(1)
        if isinstance(random_val, bytes):
            random_str = random_val.decode("utf-8", errors="replace")
        elif isinstance(random_val, str):
            random_str = random_val
        else:
            raise RuntimeError(f"Unexpected challenge response: {ttlv1}")

        binding_key, auth_token, aes_key, aes_iv = derive_quectel_session(self.device_key, random_str)

        login_payload = encode_ttlv_binary(2, auth_token.encode("utf-8"))
        req2 = build_quec_frame(CMD_LOGIN_REQ, login_payload, packet_id=self._next_packet_id())
        await self._client.write_gatt_char(QUEC_CHAR_UUID, req2, response=False)

        _pid2, _cmd2, ttlv2 = await asyncio.wait_for(self._ttlv_queue.get(), timeout=10.0)
        if ttlv2.get(3) != 0:
            raise RuntimeError(f"Quectel login failed! Code: {ttlv2.get(3)}")

        self._parser.set_encryption(aes_key, aes_iv)
        _LOGGER.debug("Quectel AES encryption activated successfully")

    def _process_telemetry_dict(self, t: dict[int, Any]) -> None:
        """Parses Struct 33/0 and dispatches data to Home Assistant."""
        v = t.get(FIELD_PACK_VOLTAGE)
        i = t.get(FIELD_PACK_CURRENT, 0.0)
        power_w = round(float(v) * float(i), 1) if (v is not None and i is not None) else 0.0

        parsed: dict[str, Any] = {
            "device_model": str(t.get(FIELD_DEVICE_MODEL, "FB-L-16")),
            "manufacturer": str(t.get(FIELD_MANUFACTURER, "Pylontech")),
            "system_sn": str(t.get(FIELD_SYSTEM_SN, "")),
            "module_sn": str(t.get(FIELD_MODULE_SN, "")),
            "rated_capacity_ah": t.get(FIELD_RATED_CAPACITY_AH, 314.0),
            "online_modules": t.get(FIELD_ONLINE_MODULES, 1),
            "total_modules": t.get(FIELD_TOTAL_MODULES, 16),
            "total_cells": t.get(FIELD_TOTAL_CELLS, 16),
            "soc": t.get(FIELD_SOC),
            "soh": t.get(FIELD_SOH, 100),
            "voltage": v,
            "cutoff_voltage": t.get(FIELD_CUTOFF_VOLTAGE),
            "current": i,
            "power": power_w,
            "suggested_charge_voltage": t.get(FIELD_SUGGESTED_CHG_V),
            "suggested_discharge_voltage": t.get(FIELD_SUGGESTED_DISCHG_V),
            "suggested_charge_current": t.get(FIELD_SUGGESTED_CHG_I),
            "suggested_discharge_current": t.get(FIELD_SUGGESTED_DISCHG_I),
            "max_charge_current_limit": t.get(FIELD_MAX_CHG_CURRENT_LIMIT),
            "max_discharge_current_limit": t.get(FIELD_MAX_DISCHG_CURRENT_LIMIT),
            "ambient_temperature": t.get(FIELD_AMBIENT_TEMP),
            "mos_temperature": t.get(FIELD_MOS_TEMP),
            "min_cell_voltage": t.get(FIELD_CELL_VOLTAGE_MIN),
            "min_cell_voltage_idx": t.get(FIELD_CELL_VOLTAGE_MIN_IDX),
            "max_cell_voltage": t.get(FIELD_CELL_VOLTAGE_MAX),
            "max_cell_voltage_idx": t.get(FIELD_CELL_VOLTAGE_MAX_IDX),
            "min_cell_temperature": t.get(FIELD_CELL_TEMP_MIN),
            "min_cell_temperature_idx": t.get(FIELD_CELL_TEMP_MIN_IDX),
            "max_cell_temperature": t.get(FIELD_CELL_TEMP_MAX),
            "max_cell_temperature_idx": t.get(FIELD_CELL_TEMP_MAX_IDX),
            "cycles": t.get(FIELD_TOTAL_CYCLES, 0),
            "energy_charged_today": t.get(FIELD_ENERGY_CHG_TODAY, 0.0),
            "energy_discharged_today": t.get(FIELD_ENERGY_DISCHG_TODAY, 0.0),
            "energy_charged_total": t.get(FIELD_ENERGY_CHG_TOTAL, 0.0),
            "energy_discharged_total": t.get(FIELD_ENERGY_DISCHG_TOTAL, 0.0),
            "max_target_soc": t.get(FIELD_MAX_TARGET_SOC, 100),
        }

        # Decode 16 Cell Voltages (mV -> V)
        cv_bytes = t.get(FIELD_CELL_VOLTAGES_BYTES)
        if isinstance(cv_bytes, str):
            cv_bytes = cv_bytes.encode("latin-1")
        if isinstance(cv_bytes, (bytes, bytearray)) and len(cv_bytes) >= 32:
            for idx in range(16):
                cell_v = struct.unpack(">H", cv_bytes[idx * 2 : (idx + 1) * 2])[0] / 1000.0
                parsed[f"cell_{idx + 1}_voltage"] = cell_v

        # Decode 16 Cell Temperatures (0.1°C -> °C)
        ct_bytes = t.get(FIELD_CELL_TEMPS_BYTES)
        if isinstance(ct_bytes, str):
            ct_bytes = ct_bytes.encode("latin-1")
        if isinstance(ct_bytes, (bytes, bytearray)) and len(ct_bytes) >= 32:
            for idx in range(16):
                cell_t = struct.unpack(">h", ct_bytes[idx * 2 : (idx + 1) * 2])[0] / 10.0
                parsed[f"cell_{idx + 1}_temperature"] = cell_t

        self.async_set_updated_data(parsed)
