# pins.py
# CircuitPython Pico pin assignments
import board
from digitalio import DigitalInOut, Pull
from adafruit_debouncer import Debouncer
from neopixel import NeoPixel

# -----------------------------
# Onboard NeoPixel LED
# -----------------------------
led = NeoPixel(board.GP22, 1)

# -----------------------------
# Button for payload execution
# -----------------------------
# Use a different GPIO than the LED
button1_pin = DigitalInOut(board.GP15)
button1_pin.switch_to_input(pull=Pull.UP)
button1 = Debouncer(button1_pin)

# -----------------------------
# Payload selection switches
# -----------------------------
payload1Pin = DigitalInOut(board.GP4)
payload1Pin.switch_to_input(pull=Pull.UP)

payload2Pin = DigitalInOut(board.GP5)
payload2Pin.switch_to_input(pull=Pull.UP)

payload3Pin = DigitalInOut(board.GP10)
payload3Pin.switch_to_input(pull=Pull.UP)

payload4Pin = DigitalInOut(board.GP11)
payload4Pin.switch_to_input(pull=Pull.UP)

# -----------------------------
# Setup / programming mode pin
# -----------------------------
progStatusPin = DigitalInOut(board.GP0)
progStatusPin.switch_to_input(pull=Pull.UP)
