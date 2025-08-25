from pynput import keyboard
import subprocess
import time
from Quartz.CoreGraphics import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGHIDEventTap,
    kCGEventFlagMaskCommand
)

def copy_to_clipboard(text):
    subprocess.run("pbcopy", text=True, input=text)

def press_cmd_v_applescript():
    applescript = 'tell application "System Events" to keystroke "v" using command down'
    subprocess.run(["osascript", "-e", applescript])

def press_cmd_v():
    try:
        v_keycode = 9
        event_down = CGEventCreateKeyboardEvent(None, v_keycode, True)
        event_up = CGEventCreateKeyboardEvent(None, v_keycode, False)
        CGEventSetFlags(event_down, kCGEventFlagMaskCommand)
        CGEventSetFlags(event_up, kCGEventFlagMaskCommand)
        CGEventPost(kCGHIDEventTap, event_down)
        CGEventPost(kCGHIDEventTap, event_up)
        return True
    except:
        return False

current_modifiers = set()

def on_press(key):
    if key in {keyboard.Key.cmd, keyboard.Key.alt}:
        current_modifiers.add(key)
    
    if key == keyboard.Key.space and current_modifiers == {keyboard.Key.cmd, keyboard.Key.alt}:
        copy_to_clipboard("hello world")
        # time.sleep(0.2)
        if not press_cmd_v():
            press_cmd_v_applescript()

def on_release(key):
    if key in current_modifiers:
        current_modifiers.remove(key)

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    print("Hotkey activated: Option + Command + Space")
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nShutting down...")
