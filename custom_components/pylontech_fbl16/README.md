# Pylontech FB-L-16 Home Assistant Custom Component

Local, cloud-free Home Assistant integration for the **Pylontech FB-L-16** (Fidus 16kWh / UF5000 / Force H3) energy storage battery over Bluetooth Low Energy (BLE).

---

## Features

- **Direct Local Bluetooth**: No cloud accounts, Wi-Fi credentials, or manufacturer bridges required.
- **Zero-Latency Stream**: Maintains a background connection via `BleakClient` and immediately updates all sensor entities when the battery broadcasts its periodic telemetry burst (~35–70s).
- **ESPHome Bluetooth Proxy Support**: Integrates directly with Home Assistant's central `bluetooth` subsystem (`bleak-retry-connector`), enabling remote reception via ESP32 Bluetooth Proxies.
- **Auto-Discovery**: Automatically recognizes `PY_FBL16_*` devices and extracts the Quectel Device Key (`dk`) from BLE advertisement packets.
- **Full Granular Diagnostics**:
  - Pack SOC (%) & SOH (%)
  - Pack Terminal Voltage (V) & Cutoff Voltage (V)
  - Pack Current (A) & Instantaneous Power (W)
  - Suggested Charging & Discharging Voltages (V)
  - Suggested Charging & Discharging Current Limits (A)
  - Inverter BMS Max Charge & Discharge Limits (A)
  - Ambient Temperature & BMS MOS Temperature (°C)
  - Min/Max Cell Voltages & Temperatures with cell index attributes
  - Daily & Total Energy Charged/Discharged (kWh) and Total Cycles
  - **All 16 Individual Cell Voltages** (`Cell 1..16 Voltage`, V)
  - **All 16 Individual Cell Temperatures** (`Cell 1..16 Temperature`, °C)

---

## Installation via HACS / Custom Component

1. Copy the `custom_components/pylontech_fbl16` folder into your Home Assistant `<config>/custom_components/` directory:
   ```text
   <config>/
   └── custom_components/
       └── pylontech_fbl16/
           ├── __init__.py
           ├── manifest.json
           ├── const.py
           ├── quectel_codec.py
           ├── coordinator.py
           ├── config_flow.py
           ├── sensor.py
           ├── strings.json
           └── translations/
               └── en.json
   ```
2. Restart Home Assistant.
3. If your Home Assistant host has a Bluetooth adapter or an ESPHome Bluetooth Proxy nearby, a notification will appear in **Settings $\rightarrow$ Devices & Services** discovering your battery (`PY_FBL16_332B`).
4. Click **Configure**, confirm the Device Key, and the battery and all 32+ sensor entities will be created immediately.

---

## Manual Configuration

If your battery is not automatically discovered:
1. Go to **Settings $\rightarrow$ Devices & Services $\rightarrow$ Add Integration**.
2. Search for **Pylontech FB-L-16 Battery**.
3. Enter your battery's Bluetooth MAC address (e.g., `B8:D0:8F:6E:FF:73`) and the Quectel Device Key (e.g., `B8D08F6F332B`).
