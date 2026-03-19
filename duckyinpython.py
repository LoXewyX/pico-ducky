# License : GPLv2.0
# copyright (c) 2023  Dave Bailey
# Author: Dave Bailey (dbisu, @daveisu)

import asyncio
import random
import re
import time

import usb_hid
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayout
from adafruit_hid.keycode import Keycode
from pins import led, progStatusPin, payload1Pin, payload2Pin, payload3Pin, payload4Pin

# Offset used to distinguish consumer-control keycodes from regular HID keycodeshelloñ
#
CONSUMER_KEY_OFFSET = 1000

# ---------------------------------------------------------------------------
# LED lock helpers
# ---------------------------------------------------------------------------

def _capsOn():
    return kbd.led_on(Keyboard.LED_CAPS_LOCK)


def _numOn():
    return kbd.led_on(Keyboard.LED_NUM_LOCK)


def _scrollOn():
    return kbd.led_on(Keyboard.LED_SCROLL_LOCK)


def pressLock(key):
    kbd.press(key)
    kbd.release(key)


def SaveKeyboardLedState():
    variables["$_INITIAL_SCROLLLOCK"] = _scrollOn()
    variables["$_INITIAL_NUMLOCK"]    = _numOn()
    variables["$_INITIAL_CAPSLOCK"]   = _capsOn()


def RestoreKeyboardLedState():
    if variables["$_INITIAL_CAPSLOCK"] != _capsOn():
        pressLock(Keycode.CAPS_LOCK)
    if variables["$_INITIAL_NUMLOCK"] != _numOn():
        pressLock(Keycode.NUM_LOCK)
    if variables["$_INITIAL_SCROLLLOCK"] != _scrollOn():
        pressLock(Keycode.SCROLL_LOCK)


# ---------------------------------------------------------------------------
# Key mappings
# ---------------------------------------------------------------------------

duckyKeys = {
    "WINDOWS":    Keycode.GUI,
    "RWINDOWS":   Keycode.RIGHT_GUI,
    "GUI":        Keycode.GUI,
    "RGUI":       Keycode.RIGHT_GUI,
    "COMMAND":    Keycode.GUI,
    "RCOMMAND":   Keycode.RIGHT_GUI,
    "APP":        Keycode.APPLICATION,
    "MENU":       Keycode.APPLICATION,
    "SHIFT":      Keycode.SHIFT,
    "RSHIFT":     Keycode.RIGHT_SHIFT,
    "ALT":        Keycode.ALT,
    "RALT":       Keycode.RIGHT_ALT,
    "OPTION":     Keycode.ALT,
    "ROPTION":    Keycode.RIGHT_ALT,
    "CONTROL":    Keycode.CONTROL,
    "CTRL":       Keycode.CONTROL,
    "RCTRL":      Keycode.RIGHT_CONTROL,
    "DOWNARROW":  Keycode.DOWN_ARROW,
    "DOWN":       Keycode.DOWN_ARROW,
    "LEFTARROW":  Keycode.LEFT_ARROW,
    "LEFT":       Keycode.LEFT_ARROW,
    "RIGHTARROW": Keycode.RIGHT_ARROW,
    "RIGHT":      Keycode.RIGHT_ARROW,
    "UPARROW":    Keycode.UP_ARROW,
    "UP":         Keycode.UP_ARROW,
    "BREAK":      Keycode.PAUSE,
    "PAUSE":      Keycode.PAUSE,
    "CAPSLOCK":   Keycode.CAPS_LOCK,
    "DELETE":     Keycode.DELETE,
    "END":        Keycode.END,
    "ESC":        Keycode.ESCAPE,
    "ESCAPE":     Keycode.ESCAPE,
    "HOME":       Keycode.HOME,
    "INSERT":     Keycode.INSERT,
    "NUMLOCK":    Keycode.KEYPAD_NUMLOCK,
    "PAGEUP":     Keycode.PAGE_UP,
    "PAGEDOWN":   Keycode.PAGE_DOWN,
    "PRINTSCREEN":Keycode.PRINT_SCREEN,
    "ENTER":      Keycode.ENTER,
    "SCROLLLOCK": Keycode.SCROLL_LOCK,
    "SPACE":      Keycode.SPACE,
    "TAB":        Keycode.TAB,
    "BACKSPACE":  Keycode.BACKSPACE,
    "A": Keycode.A,  "B": Keycode.B,  "C": Keycode.C,  "D": Keycode.D,
    "E": Keycode.E,  "F": Keycode.F,  "G": Keycode.G,  "H": Keycode.H,
    "I": Keycode.I,  "J": Keycode.J,  "K": Keycode.K,  "L": Keycode.L,
    "M": Keycode.M,  "N": Keycode.N,  "O": Keycode.O,  "P": Keycode.P,
    "Q": Keycode.Q,  "R": Keycode.R,  "S": Keycode.S,  "T": Keycode.T,
    "U": Keycode.U,  "V": Keycode.V,  "W": Keycode.W,  "X": Keycode.X,
    "Y": Keycode.Y,  "Z": Keycode.Z,
    "F1":  Keycode.F1,  "F2":  Keycode.F2,  "F3":  Keycode.F3,
    "F4":  Keycode.F4,  "F5":  Keycode.F5,  "F6":  Keycode.F6,
    "F7":  Keycode.F7,  "F8":  Keycode.F8,  "F9":  Keycode.F9,
    "F10": Keycode.F10, "F11": Keycode.F11, "F12": Keycode.F12,
    "F13": Keycode.F13, "F14": Keycode.F14, "F15": Keycode.F15,
    "F16": Keycode.F16, "F17": Keycode.F17, "F18": Keycode.F18,
    "F19": Keycode.F19, "F20": Keycode.F20, "F21": Keycode.F21,
    "F22": Keycode.F22, "F23": Keycode.F23, "F24": Keycode.F24,
}

duckyConsumerKeys = {
    "MK_VOLUP":   ConsumerControlCode.VOLUME_INCREMENT,
    "MK_VOLDOWN": ConsumerControlCode.VOLUME_DECREMENT,
    "MK_MUTE":    ConsumerControlCode.MUTE,
    "MK_NEXT":    ConsumerControlCode.SCAN_NEXT_TRACK,
    "MK_PREV":    ConsumerControlCode.SCAN_PREVIOUS_TRACK,
    "MK_PP":      ConsumerControlCode.PLAY_PAUSE,
    "MK_STOP":    ConsumerControlCode.STOP,
}

# ---------------------------------------------------------------------------
# Script state
# ---------------------------------------------------------------------------

variables = {
    "$_RANDOM_MIN":         0,
    "$_RANDOM_MAX":         65535,
    "$_EXFIL_MODE_ENABLED": False,
    "$_EXFIL_LEDS_ENABLED": False,
    "$_INITIAL_SCROLLLOCK": False,
    "$_INITIAL_NUMLOCK":    False,
    "$_INITIAL_CAPSLOCK":   False,
    "$_LED_LOCK":        True,
    "$_LED_BRIGHTNESS":     1.0,
}

# Read-only dynamic variables resolved at call time
internalVariables = {
    "$_CAPSLOCK_ON":  _capsOn,
    "$_NUMLOCK_ON":   _numOn,
    "$_SCROLLLOCK_ON": _scrollOn,
}

defines   = {}
functions = {}

letters      = "abcdefghijklmnopqrstuvwxyz"
numbers      = "0123456789"
specialChars = "!@#$%^&*()"

# ---------------------------------------------------------------------------
# IF block handler
# ---------------------------------------------------------------------------

class IF:
    def __init__(self, condition, codeIter):
        self.condition    = condition
        self.codeIter     = list(codeIter)
        self.lastIfResult = None

    def _exitIf(self):
        """Consume self.codeIter up to and including the matching END_IF."""
        depth = 0
        while self.codeIter:
            line = self.codeIter.pop(0).strip()
            if line.upper().startswith("END_IF"):
                depth -= 1
            elif line.upper().startswith("IF"):
                depth += 1
            if depth < 0:
                break
        return self.codeIter

    async def runIf(self):
        if isinstance(self.condition, str):
            self.lastIfResult = evaluateExpression(self.condition)
        elif isinstance(self.condition, bool):
            self.lastIfResult = self.condition
        else:
            raise ValueError("Invalid condition type")

        depth = 0
        while self.codeIter:
            line = self.codeIter.pop(0).strip()
            if not line:
                continue

            if line.startswith("IF"):
                depth += 1
            elif line.startswith("END_IF"):
                if depth == 0:
                    return (self.codeIter, -1)
                depth -= 1
            elif line.startswith("ELSE") and depth == 0:
                if self.lastIfResult is False:
                    remainder = line[4:].strip()  # strip leading "ELSE"
                    if remainder.startswith("IF"):
                        # ELSE IF – evaluate the nested condition
                        nestedCondition = _getIfCondition(remainder)
                        self.codeIter, self.lastIfResult = await IF(
                            nestedCondition, self.codeIter
                        ).runIf()
                        if self.lastIfResult in (-1, True):
                            return (self.codeIter, True)
                    else:
                        # Plain ELSE block
                        return await IF(True, self.codeIter).runIf()
                else:
                    # Condition was already satisfied; skip the ELSE branch
                    self._exitIf()
                    break
            elif self.lastIfResult:
                self.codeIter = list(await parseLine(line, self.codeIter))

        return (self.codeIter, self.lastIfResult)


# ---------------------------------------------------------------------------
# Script helpers
# ---------------------------------------------------------------------------

def _getIfCondition(line):
    """Extract the condition string from an 'IF <condition> THEN' line."""
    return str(line)[2:-4].strip()


def _isCodeBlock(line):
    upper = line.upper().strip()
    return upper.startswith("IF") or upper.startswith("WHILE")


def _getCodeBlock(linesIter):
    """Consume linesIter and return the lines up to the matching END_ marker."""
    code  = []
    depth = 1
    for line in linesIter:
        line = line.strip()
        if line.upper().startswith("END_"):
            depth -= 1
        elif _isCodeBlock(line):
            depth += 1
        if depth <= 0:
            break
        code.append(line)
    return code


def evaluateExpression(expression):
    """Evaluate a DuckyScript expression and return the result.

    Variable references ($NAME) are substituted before calling eval so
    that the expression uses plain Python syntax.
    """
    expression = re.sub(
        r"\$(\w+)",
        lambda m: str(variables.get("$" + m.group(1), 0)),
        expression,
    )
    expression = expression.replace("^",     "**")
    expression = expression.replace("&&",    "and")
    expression = expression.replace("||",    "or")
    expression = expression.replace("TRUE",  "True")
    expression = expression.replace("FALSE", "False")
    return eval(expression, {}, variables)


def convertLine(line):
    """Convert a space-separated key string into a list of keycodes.

    Consumer-control keycodes are stored offset by CONSUMER_KEY_OFFSET so
    they can be distinguished from regular HID keycodes in runScriptLine.
    """
    commands = []
    for key in filter(None, line.split(" ")):
        key              = key.upper()
        keycode          = duckyKeys.get(key)
        consumer_keycode = duckyConsumerKeys.get(key)
        if keycode is not None:
            commands.append(keycode)
        elif consumer_keycode is not None:
            commands.append(CONSUMER_KEY_OFFSET + consumer_keycode)
        elif hasattr(Keycode, key):
            commands.append(getattr(Keycode, key))
        else:
            print("Unknown key: <" + key + ">")
    return commands


def runScriptLine(line):
    keys = convertLine(line)
    for k in keys:
        if k > CONSUMER_KEY_OFFSET:
            consumerControl.press(k - CONSUMER_KEY_OFFSET)
        else:
            kbd.press(k)
    for k in reversed(keys):
        if k > CONSUMER_KEY_OFFSET:
            consumerControl.release()
        else:
            kbd.release(k)


def sendString(line):
    layout.write(line)


def replaceVariables(line):
    """Substitute all variable references in *line* with their current values."""
    for var, val in variables.items():
        if var in line:
            line = line.replace(var, str(val))
    for var, func in internalVariables.items():
        if var in line:
            line = line.replace(var, str(func()))
    return line


def replaceDefines(line):
    for define, value in defines.items():
        if define in line:
            line = line.replace(define, value)
    return line


# ---------------------------------------------------------------------------
# Onboard NeoPixel LED (GP25)
# ---------------------------------------------------------------------------

# Named colour presets (r, g, b) – 0-255 each
_LED_COLORS = {
    "AQUA":          (0, 255, 255),
    "BEIGE":         (245, 245, 220),
    "BLACK":         (0, 0, 0),
    "BLUE":          (0, 0, 255),
    "BROWN":         (165, 42, 42),
    "CHOCOLATE":     (210, 105, 30),
    "CORAL":         (255, 127, 80),
    "CRIMSON":       (220, 20, 60),
    "DEEP_PINK":     (255, 20, 147),
    "DEEP_PINK":     (255, 20, 147),
    "GOLD":          (255, 215, 0),
    "GOLDENROD":     (218, 165, 32),
    "GRAY":          (128, 128, 128),
    "GREEN":         (0, 255, 0),
    "DARK_GREEN":    (0, 100, 0),
    "DARK_BLUE":     (0, 0, 139),
    "DARK_CYAN":     (0, 139, 139),
    "DARK_ORANGE":   (255, 140, 0),
    "INDIGO":        (75, 0, 130),
    "IVORY":         (255, 255, 240),
    "LAVENDER":      (230, 230, 250),
    "LIGHT_BLUE":    (173, 216, 230),
    "LIGHT_PINK":    (255, 182, 193),
    "LIME":          (191, 255, 0),
    "MAGENTA":       (255, 0, 255),
    "MINT":          (189, 252, 201),
    "MIDNIGHT_BLUE": (25, 25, 112),
    "NEON_BLUE":     (0, 191, 255),
    "NEON_GREEN":    (57, 255, 20),
    "NEON_PINK":     (255, 20, 147),
    "NAVY":          (0, 0, 128),
    "OLIVE":         (128, 128, 0),
    "ORANGE":        (255, 128, 0),
    "PINK":          (255, 192, 203),
    "PLUM":          (221, 160, 221),
    "PURPLE":        (128, 0, 128),
    "ROYAL_BLUE":    (65, 105, 225),
    "SALMON":        (250, 128, 114),
    "SADDLE_BROWN":  (139, 69, 19),
    "SEA_GREEN":     (46, 139, 87),
    "SILVER":        (192, 192, 192),
    "SKY_BLUE":      (135, 206, 235),
    "SPRING_GREEN":  (0, 255, 127),
    "STEEL_BLUE":    (70, 130, 180),
    "TOMATO":        (255, 99, 71),
    "TURQUOISE":     (64, 224, 208),
    "VIOLET":        (238, 130, 238),
    "WHITE":         (255, 255, 255),
    "YELLOW":        (255, 255, 0),
}

# Last non-black colour – restored when LED toggle turns back on
_led_last_color = (255, 255, 255)

# Current colour – tracked here instead of reading led[0] which can be
# unreliable across CircuitPython versions
_led_current = (0, 0, 0)


# ---------------------------------------------------------------------------
# Core line parser
# ---------------------------------------------------------------------------

def _set_led(r, g, b):
    global _led_current

    if not variables.get("$_LED_LOCK", True):
        return

    _led_current = (r, g, b)
    led[0] = (r, g, b)

async def parseLine(line, script_lines):
    global defaultDelay, variables, functions, defines, _led_last_color, _led_current

    line = line.strip()
    if not line:
        return script_lines

    # Resolve $_RANDOM_INT before anything else
    if "$_RANDOM_INT" in line:
        line = line.replace(
            "$_RANDOM_INT",
            str(random.randint(
                int(variables.get("$_RANDOM_MIN", 0)),
                int(variables.get("$_RANDOM_MAX", 65535)),
            )),
        )

    line = replaceDefines(line)

    # ---- INJECT_MOD – strip prefix and fall through to key handler --------
    if line.startswith("INJECT_MOD"):
        line = line[11:]

    # ---- Comments ---------------------------------------------------------
    elif line.startswith("REM_BLOCK"):
        while not line.startswith("END_REM"):
            line = next(script_lines).strip()

    elif line.startswith("REM"):
        pass  # inline comment – ignore

    # ---- Key hold / release -----------------------------------------------
    elif line.startswith("HOLD"):
        key     = line[5:].strip().upper()
        keycode = duckyKeys.get(key)
        if keycode:
            kbd.press(keycode)
        else:
            print("Unknown key to HOLD: <" + key + ">")

    elif line.startswith("RELEASE"):
        key     = line[8:].strip().upper()
        keycode = duckyKeys.get(key)
        if keycode:
            kbd.release(keycode)
        else:
            print("Unknown key to RELEASE: <" + key + ">")

    # ---- Timing -----------------------------------------------------------
    elif line.startswith("DELAY"):
        time.sleep(float(replaceVariables(line)[6:]) / 1000)

    # ---- Multi-line STRINGLN block ----------------------------------------
    elif line == "STRINGLN":
        line = next(script_lines, None)
        while line and not line.startswith("END_STRINGLN"):
            sendString(line)
            kbd.press(Keycode.ENTER)
            kbd.release(Keycode.ENTER)
            line = next(script_lines, None)

    # ---- Single-line STRINGLN ---------------------------------------------
    elif line.startswith("STRINGLN"):
        sendString(replaceVariables(line[9:]))
        kbd.press(Keycode.ENTER)
        kbd.release(Keycode.ENTER)

    # ---- Multi-line STRING block ------------------------------------------
    elif line == "STRING":
        line = replaceVariables(next(script_lines).strip())
        while not line.startswith("END_STRING"):
            sendString(line)
            line = replaceDefines(replaceVariables(next(script_lines).strip()))

    # ---- Single-line STRING -----------------------------------------------
    elif line.startswith("STRING"):
        sendString(replaceVariables(line[7:]))

    # ---- Debug print ------------------------------------------------------
    elif line.startswith("PRINT"):
        print("[SCRIPT]: " + replaceVariables(line[6:]))

    # ---- Import / run another script file ---------------------------------
    elif line.startswith("IMPORT"):
        await runScript(line[7:])

    # ---- Default delays ---------------------------------------------------
    elif line.startswith("DEFAULT_DELAY"):
        defaultDelay = int(line[14:]) * 10

    elif line.startswith("DEFAULTDELAY"):
        defaultDelay = int(line[13:]) * 10

    # ---- LED control ------------------------------------------------------
    elif line.startswith("LED_BRIGHTNESS"):
        # LED_BRIGHTNESS <float>  – 0.0 (off) to 1.0 (full brightness)
        try:
            value = float(replaceVariables(line[15:].strip()))
            if value < 0:
                value = 0.0
            elif value > 1:
                value = 1.0
            variables["$_LED_BRIGHTNESS"] = value
            led.brightness = value
        except ValueError:
            print("Invalid LED_BRIGHTNESS value:", line[15:].strip())

    elif line.startswith("LED_OFF"):
        _set_led(0, 0, 0)

    elif line.startswith("LED_COLOR"):
        parts = line.split(None, 1)
        if len(parts) == 2:
            rgb = _LED_COLORS.get(parts[1].strip().upper())
            if rgb:
                _set_led(*rgb)
                _led_last_color = _led_current
            else:
                print("Unknown LED colour: " + parts[1].strip())

    elif line.startswith("LED_RGB"):
        parts = line.split()
        if len(parts) == 4:
            r = int(evaluateExpression(replaceVariables(parts[1])))
            g = int(evaluateExpression(replaceVariables(parts[2])))
            b = int(evaluateExpression(replaceVariables(parts[3])))
            _set_led(r, g, b)
            _led_last_color = _led_current
        else:
            print("LED_RGB expects 3 values: LED_RGB <r> <g> <b>")

    elif line.startswith("LED_R"):
        _set_led(255, 0, 0)

    elif line.startswith("LED_G"):
        _set_led(0, 255, 0)

    # ---- Variable declaration ---------------------------------------------
    elif line.startswith("VAR"):
        match = re.match(r"VAR\s+\$(\w+)\s*=\s*(.+)", line)
        if match:
            variables["$" + match.group(1)] = evaluateExpression(match.group(2))
        else:
            raise SyntaxError("Invalid variable declaration: " + line)

    # ---- Variable assignment ----------------------------------------------
    elif line.startswith("$"):
        match = re.match(r"\$(\w+)\s*=\s*(.+)", line)
        if match:
            variables["$" + match.group(1)] = evaluateExpression(match.group(2))
        else:
            raise SyntaxError(
                "Invalid variable update, declare variable first: " + line
            )

    # ---- DEFINE alias -----------------------------------------------------
    elif line.startswith("DEFINE"):
        parts = line.split(" ", 2)
        if len(parts) == 3:
            defines[parts[1]] = parts[2]

    # ---- Function definition ----------------------------------------------
    elif line.startswith("FUNCTION"):
        func_name          = line.split()[1]
        functions[func_name] = []
        line = next(script_lines).strip()
        while line != "END_FUNCTION":
            functions[func_name].append(line)
            line = next(script_lines).strip()

    # ---- WHILE loop -------------------------------------------------------
    elif line.startswith("WHILE"):
        condition = line[5:].strip()
        loopCode  = list(_getCodeBlock(script_lines))
        while evaluateExpression(condition):
            currentIterCode = list(loopCode)
            while currentIterCode:
                loopLine        = currentIterCode.pop(0)
                currentIterCode = list(
                    await parseLine(loopLine, iter(currentIterCode))
                )

    # ---- IF block ---------------------------------------------------------
    elif line.upper().startswith("IF"):
        script_lines, _ret = await IF(_getIfCondition(line), script_lines).runIf()

    elif line.upper().startswith("END_IF"):
        pass  # consumed by IF handler; silently ignore any stragglers

    # ---- Random character helpers -----------------------------------------
    elif line == "RANDOM_LOWERCASE_LETTER":
        sendString(random.choice(letters))

    elif line == "RANDOM_UPPERCASE_LETTER":
        sendString(random.choice(letters.upper()))

    elif line == "RANDOM_LETTER":
        sendString(random.choice(letters + letters.upper()))

    elif line == "RANDOM_NUMBER":
        sendString(random.choice(numbers))

    elif line == "RANDOM_SPECIAL":
        sendString(random.choice(specialChars))

    elif line == "RANDOM_CHAR":
        sendString(random.choice(letters + letters.upper() + numbers + specialChars))

    elif line in ("VID_RANDOM", "PID_RANDOM"):
        for _ in range(4):
            sendString(random.choice("0123456789ABCDEF"))

    elif line in ("MAN_RANDOM", "PROD_RANDOM"):
        for _ in range(12):
            sendString(random.choice(letters + letters.upper() + numbers))

    elif line == "SERIAL_RANDOM":
        for _ in range(12):
            sendString(random.choice(letters + letters.upper() + numbers + specialChars))

    # ---- Keyboard state ---------------------------------------------------
    elif line == "RESET":
        kbd.release_all()

    elif line == "SAVE_HOST_KEYBOARD_LOCK_STATE":
        SaveKeyboardLedState()

    elif line == "RESTORE_HOST_KEYBOARD_LOCK_STATE":
        RestoreKeyboardLedState()

    elif line == "WAIT_FOR_SCROLL_CHANGE":
        last_scroll = _scrollOn()
        while _scrollOn() == last_scroll:
            await asyncio.sleep(0.01)

    # ---- User-defined function call ---------------------------------------
    elif line in functions:
        func_iter = iter(list(functions[line]))
        while True:
            try:
                func_line = next(func_iter)
            except StopIteration:
                break
            result = await parseLine(func_line, func_iter)
            # parseLine may return a list (e.g. after an IF block); wrap it back
            if isinstance(result, list):
                func_iter = iter(result)
            else:
                func_iter = result

    # ---- Fallback: key combination ----------------------------------------
    else:
        runScriptLine(line)

    return script_lines


# ---------------------------------------------------------------------------
# HID device initialisation  (must come after all helper definitions)
# ---------------------------------------------------------------------------

kbd             = Keyboard(usb_hid.devices)
consumerControl = ConsumerControl(usb_hid.devices)
layout          = KeyboardLayout(kbd)

# Onboard NeoPixel – wrapped in try/except so a bad pin name never crashes
# the whole program.  If init fails a no-op stub is used instead and the
# error is printed to the serial console.
class _DummyLed:
    """Silent stub used when NeoPixel initialisation fails."""
    def __init__(self):
        self._c = (0, 0, 0)
    def __setitem__(self, i, v):
        self._c = v
    def __getitem__(self, i):
        return self._c
    def brightness(self, v):
        self._c = (int(v * self._c[0]), int(v * self._c[1]), int(v * self._c[2]))
    def show(self):
        pass
    def deinit(self):
        pass

try:
    led[0] = (0, 0, 0)
except Exception as e:
    print("LED commands will be silent until the pin is fixed.")
    led = _DummyLed()


def getProgrammingStatus():
    return not progStatusPin.value


defaultDelay = 0


# ---------------------------------------------------------------------------
# Script runner
# ---------------------------------------------------------------------------

async def runScript(file):
    global defaultDelay

    # LOCK LED CONTROL
    variables["$_LED_LOCK"] = True

    restart = True
    try:
        while restart:
            restart = False
            with open(file, "r", encoding="utf-8") as f:
                script_lines = iter(f.readlines())
                previousLine = ""
                while True:
                    try:
                        line = next(script_lines)
                    except StopIteration:
                        break

                    if line.startswith("REPEAT"):
                        count = int(line[7:].strip())
                        for _ in range(count):
                            await parseLine(previousLine, iter([]))
                            time.sleep(float(defaultDelay) / 1000)

                    elif line.startswith("RESTART_PAYLOAD"):
                        restart = True
                        break

                    elif line.startswith("STOP_PAYLOAD"):
                        break

                    else:
                        result = await parseLine(line, script_lines)
                        # parseLine may return a list of remaining lines (e.g. after
                        # an IF block consumed the original iterator).  Rebuild the
                        # iterator so that subsequent lines are not lost.
                        if isinstance(result, list):
                            script_lines = iter(result)
                        previousLine = line

                    time.sleep(float(defaultDelay) / 1000)

    except OSError:
        print("Unable to open file", file)

    # UNLOCK LED CONTROL
    variables["$_LED_LOCK"] = False
    led.deinit()


# ---------------------------------------------------------------------------
# Payload selection
# ---------------------------------------------------------------------------

def selectPayload():
    if not payload1Pin.value:
        return "payload.dd"
    if not payload2Pin.value:
        return "payload2.dd"
    if not payload3Pin.value:
        return "payload3.dd"
    if not payload4Pin.value:
        return "payload4.dd"
    # No switch active – default to payload 1
    return "payload.dd"


# ---------------------------------------------------------------------------
# Button monitor task
# ---------------------------------------------------------------------------

async def monitor_buttons(button1):
    print("starting monitor_buttons")
    button1Down = False
    while True:
        button1.update()

        if button1.fell:
            print("Button 1 pushed")
            button1Down = True

        if button1.rose:
            print("Button 1 released")
            if button1Down:
                payload = selectPayload()
                print("Running", payload)
                await runScript(payload)
                print("Done")
            button1Down = False

        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# Exfil LED-encoding monitor task
# ---------------------------------------------------------------------------

async def monitor_led_changes():
    print("starting monitor_led_changes")
    while True:
        if variables.get("$_EXFIL_MODE_ENABLED"):
            try:
                bit_list          = []
                last_caps_state   = _capsOn()
                last_num_state    = _numOn()
                last_scroll_state = _scrollOn()

                with open("loot.bin", "ab") as f:
                    while variables.get("$_EXFIL_MODE_ENABLED"):
                        caps_state   = _capsOn()
                        num_state    = _numOn()
                        scroll_state = _scrollOn()

                        if caps_state != last_caps_state:
                            bit_list.append(0)
                            last_caps_state = caps_state
                        elif num_state != last_num_state:
                            bit_list.append(1)
                            last_num_state = num_state

                        if len(bit_list) == 8:
                            byte = 0
                            for b in bit_list:
                                byte = (byte << 1) | b
                            f.write(bytes([byte]))
                            bit_list = []

                        if scroll_state != last_scroll_state:
                            variables["$_EXFIL_LEDS_ENABLED"] = False
                            break

                        await asyncio.sleep(0.001)
            except Exception as e:
                print("Error in monitor_led_changes:", e)

        await asyncio.sleep(0)
