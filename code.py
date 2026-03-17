# License : GPLv2.0
# copyright (c) 2023  Dave Bailey
# Author: Dave Bailey (dbisu, @daveisu)
# Pico board support only

import asyncio
import os
import time

import supervisor
from duckyinpython import getProgrammingStatus, selectPayload, runScript, monitor_buttons, monitor_led_changes
from pins import button1

# Sleep at start to allow host recognition
time.sleep(0.5)

# Turn off auto-reload
supervisor.runtime.autoreload = False

async def run_payload_on_startup():
    progStatus = getProgrammingStatus()
    print("progStatus", progStatus)
    if not progStatus:
        print("Finding payload")
        if "loot.bin" in os.listdir("/"):
            print("loot.bin exists, skipping payload execution.")
        else:
            payload = selectPayload()
            await asyncio.sleep(0.1)
            print("Running payload")
            await runScript(payload)
    else:
        print("Done")


async def main_loop():
    # Start tasks
    button_task    = asyncio.create_task(monitor_buttons(button1))
    payload_task   = asyncio.create_task(run_payload_on_startup())
    led_task       = asyncio.create_task(monitor_led_changes())

    await asyncio.gather(button_task, payload_task, led_task)


asyncio.run(main_loop())
