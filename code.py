# License : GPLv2.0
# copyright (c) 2023  Dave Bailey
# Author: Dave Bailey (dbisu, @daveisu)

import asyncio
import os
import time

import supervisor
from duckyinpython import (
    getProgrammingStatus,
    selectPayload,
    runScript,
    monitor_buttons,
    monitor_led_changes
)

# Sleep at start to allow host recognition
time.sleep(0.5)

# --- Exit immediately if drive.lock exists ---
if "drive.lock" in os.listdir("/"):
    print("drive.lock detected: exiting code.py")
    while True:
        time.sleep(1)  # Stop execution safely

# --- Disable auto-reload ---
supervisor.runtime.autoreload = False

# --- Payload runner ---
async def run_payload_on_startup():
    progStatus = getProgrammingStatus()
    print("progStatus:", progStatus)
    if not progStatus:
        if "loot.bin" in os.listdir("/"):
            print("loot.bin exists, skipping payload execution.")
        else:
            payload = selectPayload()
            await asyncio.sleep(0.1)
            print("Running payload")
            await runScript(payload)
    else:
        print("Done")

# --- Main async loop ---
async def main_loop():
    tasks = [
        asyncio.create_task(monitor_buttons()),
        asyncio.create_task(run_payload_on_startup()),
        asyncio.create_task(monitor_led_changes())
    ]
    await asyncio.gather(*tasks)

with open("/run", "r") as f:
    run_flag = f.read()

# --- Run main loop ---
if run_flag == "1":
    asyncio.run(main_loop())
