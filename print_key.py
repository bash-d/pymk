#!/usr/bin/python3
import keyboard

def callback(e):
    print(e)
    print(e.scan_code)

keyboard.hook(callback)
keyboard.wait()
