# License : GPLv2.0
# copyright (c) 2023  Dave Bailey
# Author: Dave Bailey (dbisu, @daveisu)

from board import GP15
import digitalio
import storage
import os


# ---------- Helpers ----------

def ensure_dir(path):
    if path.strip("/") not in os.listdir("/"):
        try:
            os.mkdir(path)
        except OSError as e:
            print(f"Failed to create {path}:", e)


def write_var(name, value):
    try:
        with open(f"/var/{name}", "w") as f:
            f.write(value)
    except OSError as e:
        print(f"Failed to write /var/{name}:", e)


def is_exfil_enabled(payload_path="payload.dd"):
    try:
        with open(payload_path, "r") as f:
            for line in f:
                if "$_EXFIL_MODE_ENABLED" in line and "TRUE" in line.upper():
                    return True
    except OSError:
        pass
    return False


def read_attack_mode():
    try:
        with open("payload.dd", "r") as f:
            parts = f.readline().strip().split()
            if parts and parts[0] == "ATTACKMODE":
                return parts[1:]
    except OSError:
        pass
    return []


# ---------- Setup ----------

ensure_dir("/var")

noStoragePin = digitalio.DigitalInOut(GP15)
noStoragePin.switch_to_input(pull=digitalio.Pull.UP)
noStorageStatus = noStoragePin.value

exfil_enabled = is_exfil_enabled()
loot_exists = "loot.bin" in os.listdir("/")

modes = read_attack_mode()


# ---------- Main Logic ----------

if not noStorageStatus:
    write_var("run", "1")
    storage.enable_usb_drive()

elif len(modes) > 0:
    if modes == ["STORAGE"] or modes == ["HID", "STORAGE"]:
        write_var("run", "0")
        storage.enable_usb_drive()

    elif modes == ["HID"] or modes == ["OFF"]:
        write_var("run", "1")
        storage.disable_usb_drive()

    else:
        print(f"Unknown ATTACKMODE: <{modes}>")

else:
    write_var("run", "1")
