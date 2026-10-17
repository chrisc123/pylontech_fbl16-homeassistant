# Pylontech FB-L-16 Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A local, cloud-free Home Assistant integration for the **Pylontech FB-L-16** (Fidus 16kWh / UF5000 / Force H3) energy storage battery over Bluetooth Low Energy (BLE).

---

## Features

- **100% Local & Cloud-Free**: Communicates directly with the battery's onboard Quectel BLE module. No cloud accounts, manufacturer bridges, or Wi-Fi connections required.
- **Auto-Discovery**: Automatically discovers `PY_FBL16_*` batteries broadcasting nearby and auto-populates the Quectel Device Key (`dk`).
- **ESPHome Bluetooth Proxy Support**: Fully compatible with Home Assistant's native Bluetooth subsystem (`bleak-retry-connector`). Works via local Bluetooth dongles or ESPHome Bluetooth Proxies.
- **Streaming Telemetry**: Subscribes directly to the battery's periodic broadcast stream (~35–70s intervals), updating entities instantaneously without active polling overhead.
- **Comprehensive Sensors (32+ Entities)**:
  - **Pack State**: State of Charge (%), State of Health (%), Terminal Voltage (V), Cutoff Voltage (V), Current (A), Instantaneous Power (W).
  - **Inverter Guidance Limits**: Suggested Charging & Discharging Voltages (V), Suggested Charging & Discharging Current Limits (A), Inverter BMS Max Limits (A).
  - **Temperatures**: Ambient Temperature (°C), BMS MOS Temperature (°C), Min/Max Cell Temperatures with cell index attributes.
  - **Cell Diagnostics**: Min/Max Cell Voltages (V) with index attributes.
  - **Individual Cell Voltages**: Full telemetry for all 16 cells (`Cell 1..16 Voltage` in V).
  - **Individual Cell Temperatures**: Full telemetry for all 16 cells (`Cell 1..16 Temperature` in °C).
  - **Energy & Statistics**: Daily & Total Energy Charged / Discharged (kWh), Total Cycle Count.

---

## Installation

### Method 1: HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. In Home Assistant, open **HACS** $\rightarrow$ **Integrations**.
3. Click the three dots in the top right corner and select **Custom repositories**.
4. Add `https://github.com/chrisc123/pylontech_fbl16-homeassistant` with Category **Integration**.
5. Click **Download**, then restart Home Assistant.

### Method 2: Manual Installation

1. Copy the `custom_components/pylontech_fbl16` folder into your Home Assistant `/config/custom_components/` directory:
   ```text
   /config/
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

---

## Configuration

### Automatic Discovery

1. Ensure the Pylontech mobile app is **closed** on your phone (the battery only supports one active Bluetooth connection at a time).
2. Go to **Settings $\rightarrow$ Devices & Services**.
3. A discovery notification will appear for **Pylontech FB-L-16 Battery** (e.g. `PY_FBL16_332B`).
4. Click **Configure**, confirm the Device Key, and click **Submit**.

### Manual Setup

If the battery is not discovered automatically:
1. Go to **Settings $\rightarrow$ Devices & Services $\rightarrow$ Add Integration**.
2. Search for **Pylontech FB-L-16 Battery**.
3. Enter your battery's Bluetooth MAC address (e.g. `B8:D0:8F:6E:FF:73`) and the Quectel Device Key (e.g. `B8D08F6F332B`).

---

## Important Notes & Troubleshooting

> [!IMPORTANT]
> **Single Bluetooth Connection Limit**: The Pylontech battery BMS allows only **one** simultaneous Bluetooth connection. If the official mobile app is connected to the battery, Home Assistant will be blocked from connecting. Close or force-stop the mobile app when using this integration.

> [!NOTE]
> **Initial Telemetry Broadcast**: The battery sends telemetry packets approximately every 35 to 70 seconds. When the integration first connects, entity values will populate as soon as the first broadcast packet is received.

---

## Technical Details

The FB-L-16 battery uses a Quectel Bluetooth Low Energy module communicating over GATT service `0x180A` and characteristic `0x9C40`:
- **Authentication**: 2-step challenge-response handshake (`0x7032` request $\rightarrow$ random challenge $\rightarrow$ SHA-256 token derivation $\rightarrow$ `0x7034` login).
- **Encryption**: AES-128-CBC with PKCS7 padding and Quectel byte-stuffing (`0xAA 0x55`).
- **Telemetry**: Frame command `0x0014` containing Quectel TTLV Struct 33 / Struct 0.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
