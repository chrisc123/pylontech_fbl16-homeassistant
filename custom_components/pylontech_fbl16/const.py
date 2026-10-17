"""Constants for the Pylontech FB-L-16 integration."""

from typing import Final

DOMAIN: Final = "pylontech_fbl16"

# Quectel Custom BLE GATT Service & Characteristics (Mode A)
QUEC_SERVICE_UUID: Final = "0000180a-0000-1000-8000-00805f9b34fb"
QUEC_CHAR_UUID: Final = "00009c40-0000-1000-8000-00805f9b34fb"

# Manufacturer data tag for Quectel BLE: 0x5551 ("QU")
QUEC_MFG_ID: Final = 0x5551

# Quectel Command IDs
CMD_TRANSPARENT_TX: Final = 0x0023  # App -> Device (Modbus RTU over Quectel)
CMD_TRANSPARENT_RX: Final = 0x0024  # Device -> App (Modbus RTU over Quectel)
CMD_CHALLENGE_REQ: Final = 0x7032   # Request 16-char random challenge
CMD_CHALLENGE_RESP: Final = 0x7033  # Response with random challenge
CMD_LOGIN_REQ: Final = 0x7034       # Send authToken to authenticate
CMD_LOGIN_RESP: Final = 0x7035      # Authentication result (id 3: 0=success)
CMD_TELEMETRY_STREAM: Final = 0x0014 # Unsolicited live battery telemetry broadcast

# Configuration Flow Keys
CONF_DEVICE_KEY: Final = "device_key"
CONF_PRODUCT_KEY: Final = "product_key"

# Primary Telemetry Field IDs inside Struct 33 / Struct 0
FIELD_DEVICE_MODEL: Final = 1          # e.g. "FBL16"
FIELD_MANUFACTURER: Final = 2          # e.g. "Pylon"
FIELD_SYSTEM_SN: Final = 3             # e.g. "H260801CB0020216"
FIELD_RATED_CAPACITY_AH: Final = 8     # e.g. 314.0 Ah
FIELD_TOTAL_MODULES: Final = 11        # Total installed modules (e.g. 16)
FIELD_TOTAL_CELLS: Final = 12          # Total cells (e.g. 16)
FIELD_ONLINE_MODULES: Final = 14       # Online modules (e.g. 1)
FIELD_PACK_VOLTAGE: Final = 16         # Terminal Pack Voltage (V)
FIELD_CUTOFF_VOLTAGE: Final = 18       # Cutoff / Bus Voltage (V)
FIELD_PACK_CURRENT: Final = 19         # Pack Current (A)
FIELD_CELL_VOLTAGE_MIN: Final = 20     # Min Cell Voltage (V)
FIELD_CELL_TEMP_MIN: Final = 21        # Min Cell Temperature (°C)
FIELD_AMBIENT_TEMP: Final = 22         # Ambient Temperature (°C)
FIELD_MOS_TEMP: Final = 23             # BMS MOS Temperature (°C)
FIELD_SUGGESTED_CHG_V: Final = 24      # Suggested Charging Voltage (V)
FIELD_SUGGESTED_DISCHG_V: Final = 25   # Suggested Discharging Voltage (V)
FIELD_SUGGESTED_CHG_I: Final = 26      # Suggested Charging Current (A)
FIELD_SUGGESTED_DISCHG_I: Final = 27   # Suggested Discharging Current (A)
FIELD_SOC: Final = 30                  # State of Charge (%)
FIELD_SOH: Final = 32                  # State of Health (%)
FIELD_CELL_VOLTAGE_MAX: Final = 35     # Max Cell Voltage (V)
FIELD_CELL_VOLTAGE_MAX_IDX: Final = 36 # Max Cell Voltage 1-based index
FIELD_CELL_VOLTAGE_MIN_IDX: Final = 38 # Min Cell Voltage 1-based index
FIELD_CELL_TEMP_MAX: Final = 39        # Max Cell Temperature (°C)
FIELD_CELL_TEMP_MAX_IDX: Final = 40    # Max Cell Temp 1-based index
FIELD_CELL_TEMP_MIN_IDX: Final = 42    # Min Cell Temp 1-based index
FIELD_MAX_CHG_CURRENT_LIMIT: Final = 43    # BMS Max Inverter Charge Limit (A)
FIELD_MAX_DISCHG_CURRENT_LIMIT: Final = 44 # BMS Max Inverter Discharge Limit (A)
FIELD_TOTAL_CYCLES: Final = 45         # Cycle count (0)
FIELD_ENERGY_CHG_TODAY: Final = 47     # Daily energy charged (kWh)
FIELD_ENERGY_DISCHG_TODAY: Final = 48  # Daily energy discharged (kWh)
FIELD_ENERGY_CHG_TOTAL: Final = 51     # Lifetime energy charged (kWh)
FIELD_ENERGY_DISCHG_TOTAL: Final = 52  # Lifetime energy discharged (kWh)
FIELD_CELL_VOLTAGES_BYTES: Final = 99  # 16x uint16 big-endian mV (32 bytes)
FIELD_CELL_TEMPS_BYTES: Final = 100    # 16x int16 big-endian 0.1°C (32 bytes)
FIELD_MODULE_SN: Final = 101           # Module Serial Number string
FIELD_MAX_TARGET_SOC: Final = 161      # Target / Max Charge SOC (%)
FIELD_GRID_CUTOFF_SOC: Final = 162     # Grid Cutoff SOC (%)
FIELD_RESERVE_SOC: Final = 163         # Backup Reserve SOC (%)
FIELD_HEATER_STATE: Final = 164        # Heater state (0=Off, 1=On)
