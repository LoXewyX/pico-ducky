# License : GPLv2.0
# copyright (c) 2023  Dave Bailey
# Author: Dave Bailey (dbisu, @daveisu)
# Pico and Pico W board support

from board import GP15
import digitalio
import storage
import os

def is_exfil_enabled(payload_path="payload.dd"):
    try:
        with open(payload_path, "r") as f:
            for line in f:
                if "$_EXFIL_MODE_ENABLED" in line and "TRUE" in line.upper():
                    return True
    except OSError:
        pass
    return False

exfil_enabled = is_exfil_enabled()
loot_exists = "loot.bin" in os.listdir("/")
noStorage = False

noStoragePin = digitalio.DigitalInOut(GP15)
noStoragePin.switch_to_input(pull=digitalio.Pull.UP)
noStorageStatus = noStoragePin.value

print(noStorageStatus)

if not "run" in os.listdir("/"):
    with open("/run", "w") as f:
        f.write("0")

with open("payload.dd", "r") as f:
    parts = f.readline().strip().split()

    if not noStorageStatus:
        with open("/run", "w") as f:
            f.write("0")

    elif parts and parts[0] == "ATTACKMODE":
        modes = parts[1:]

        if modes == ["STORAGE"] or modes == ["HID", "STORAGE"]:
            with open("/run", "w") as f:
                f.write("0")
            storage.enable_usb_drive()
        elif modes == ["HID"] or modes == ["OFF"]:
            with open("/run", "w") as f:
                f.write("1")
            storage.disable_usb_drive()
        else:
            print(f"Unknown ATTACKMODE: <{modes}>")

    else:
        with open("/run", "w") as f:
            f.write("1")
