#!/usr/bin/env python3
#import pynput
#import keyboard

from pynput import keyboard

def get_vk(key):
    """
    Get the virtual key code from a key.
    These are used so case/shift modifications are ignored.
    """
    return key.vk if hasattr(key, 'vk') else key.value.vk
    

# The key hotkeys to look for
class Listener:
    def __init__(self):
        self.layer = 0
        self.binds = [
            [
                ((keyboard.Key.shift, keyboard.KeyCode(vk=65)), (), 'press')  # shift + a
            ]
        ]

        self.pressed_vks = set()

        on_press_callback = lambda key: self.on_press(key)
        on_release_callback = lambda key: self.on_release(key)

        with keyboard.Listener(
                on_press=on_press_callback,
                on_release=on_release_callback) as listener:
            listener.join()

    
    def is_hotkey_pressed(self, hotkey):
        k = []
        print(hotkey)
        for key in hotkey:
            k.append(get_vk(key) in self.pressed_vks)
        return all(k)
        #return all([get_vk(key) in self.pressed_vks for key in hotkey])
    
    
    def on_press(self, key):
        """ When a key is pressed """
        vk = get_vk(key)  # Get the key's vk
        self.pressed_vks.add(vk)  # Add it to the set of currently pressed keys
    
        for bind in self.binds[self.layer]: # Loop through each bind in the layer 
                bind_hotkey = bind[0]
                bind_type = bind[2]
                if self.is_hotkey_pressed(bind_hotkey) and bind_type == 'press':  # And check if all keys are pressed
                    print("On press hotkey")
                    break  # Don't allow execute to be called more than once per key press
    
    
    def on_release(self, key):
        """ When a key is released """
        vk = get_vk(key)  # Get the key's vk
        try:
            self.pressed_vks.remove(vk)  # Remove it from the set of currently pressed keys
        except:
            pass
        #for hotkey in binds:  # Loop though each hotkey
        #    if is_hotkey_pressed(hotkey) and hotkey['type'] == 'release':  # And check if all keys are pressed
        #        print("On release hotkey")
        #        break  # Don't allow execute to be called more than once per key press


Listener()
