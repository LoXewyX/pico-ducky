# License : GPLv2.0
# copyright (c) 2023  Dave Bailey
# Author: Dave Bailey (dbisu, @daveisu)
# Pico board support only

import os

import digitalio
import storage
from board import GP15


def is_exfil_enabled(payload_path="payload.dd"):
    try:
        with open(payload_path, "r") as f:
            for line in f:
                if "$_EXFIL_MODE_ENABLED" in line and "TRUE" in line.upper():
                    return True
    except OSError:
        pass
    return False


# Check if exfiltration is enabled in payload
exfil_enabled = is_exfil_enabled()

# Check if loot file exists
loot_exists = "loot.bin" in os.listdir("/")

# Setup GP15 input to control USB visibility
noStoragePin = digitalio.DigitalInOut(GP15)
noStoragePin.switch_to_input(pull=digitalio.Pull.UP)
noStorage = not noStoragePin.value  # True if connected to GND

# Disable USB drive if exfil is enabled and loot.bin doesn't exist
if exfil_enabled and not loot_exists:
    storage.disable_usb_drive()

# Disable USB drive based on GP15 pin
if noStorage:
    storage.disable_usb_drive()
