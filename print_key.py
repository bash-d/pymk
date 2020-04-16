#!/usr/bin/python3
import keyboard

def callback(e):
    print(keyboard._pressed_events)

keyboard.hook(callback)
keyboard.wait()
