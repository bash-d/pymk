#!/usr/bin/python3

import platform
import keyboard
import subprocess
import re
import unicodedata
from keyboard import _pressed_events, _pressed_events_lock, KEY_DOWN, KEY_UP, is_modifier

# Custom function replacing keyboard/__init__.py _KeyboardListener.direct_callback
def custom_direct_callback(self, event):
    print("Custom")
    """
    This function is called for every OS keyboard event and decides if the
    event should be blocked or not, and passes a copy of the event to
    other, non-blocking, listeners.

    There are two ways to block events: remapped keys, which translate
    events by suppressing and re-emitting; and blocked hotkeys, which
    suppress specific hotkeys.
    """
    # Pass through all fake key events, don't even report to other handlers.
    if self.is_replaying:
        return True

    # MODIFIED PART
    # captures keyboard events even if a hook is suppressing
    event_type = event.event_type
    scan_code = event.scan_code

    # Update tables of currently pressed keys and modifiers.
    with _pressed_events_lock:
        if event_type == KEY_DOWN:
            if is_modifier(scan_code): self.active_modifiers.add(scan_code)
            _pressed_events[scan_code] = event
        hotkey = tuple(sorted(_pressed_events))
        if event_type == KEY_UP:
            self.active_modifiers.discard(scan_code)
            if scan_code in _pressed_events: del _pressed_events[scan_code]

    if not all(hook(event) for hook in self.blocking_hooks):
        return False

    # Mappings based on individual keys instead of hotkeys.
    for key_hook in self.blocking_keys[scan_code]:
        if not key_hook(event):
            return False

    # Default accept.
    accept = True

    if self.blocking_hotkeys:
        if self.filtered_modifiers[scan_code]:
            origin = 'modifier'
            modifiers_to_update = set([scan_code])
        else:
            modifiers_to_update = self.active_modifiers
            if is_modifier(scan_code):
                modifiers_to_update = modifiers_to_update | {scan_code}
            callback_results = [callback(event) for callback in self.blocking_hotkeys[hotkey]]
            if callback_results:
                accept = all(callback_results)
                origin = 'hotkey'
            else:
                origin = 'other'

        for key in sorted(modifiers_to_update):
            transition_tuple = (self.modifier_states.get(key, 'free'), event_type, origin)
            should_press, new_accept, new_state = self.transition_table[transition_tuple]
            if should_press: press(key)
            if new_accept is not None: accept = new_accept
            self.modifier_states[key] = new_state

    if accept:
        if event_type == KEY_DOWN:
            _logically_pressed_keys[scan_code] = event
        elif event_type == KEY_UP and scan_code in _logically_pressed_keys:
            del _logically_pressed_keys[scan_code]

    # Queue for handlers that won't block the event.
    self.queue.put(event)

    return accept

def disable_x_input():
    xinput_dev = subprocess.run(['xinput', '--list'], stdout=subprocess.PIPE, text=True)
    xinput_dev = xinput_dev.stdout
    
    # filter out keyboard xinput devices
    kb_dev = re.findall(r'.*keyboard.*\n', xinput_dev)[1:]
    kb_dict = {}
    
    print("id\tenabled\t\tname")
    for dev in kb_dev:
        # get id and name of each keyboard device
        kb = re.search(r'.*↳ (.+?)id=([0-9]+).*\n', dev)
        kb_id = kb.group(2)
        kb_name = kb.group(1)
    
        # get status of keyboard devices (enabled=1/disabled=0)
        props = subprocess.run(['xinput', 'list-props', kb_id], stdout=subprocess.PIPE, text=True)
        props = props.stdout
        kb_status = re.search(r'Device Enabled \([0-9]+\):\t[01]\n', props).group()[-2:]
        kb_status = int(kb_status.replace('\n', ''))
    
        kb_dict[kb_id] = [kb_name, kb_status]
        print("[{}]\t[{}]\t\t{}".format(kb_id, kb_status, kb_name))
    
    # disable keyboard for xinput
    kb_id = input("Keyboard to disable: ")
    if kb_id in kb_dict:
        kb_name = kb_dict[kb_id][0]
        kb_status = kb_dict[kb_id][1]
        if kb_status == 1:
            subprocess.run(['xinput', '--disable', kb_id])
            print("Disabling: {} id={}".format(kb_name, kb_id))
        return kb_id
    else:
        print("Keyboard not found")
        quit()

# 58 caps locks
# 54 right shift
# 53 /
# 41 `

# 58 = mod key
# toggle(just tap defined on both layers),tap,momentary
# 1 = layer\function

# True - when unbound key in pressed its default key will be sent
# False - send nothing if an unbound key is pressed
key_fallback = [True,
                False,
]

mod_keys = [{58:['momentary', 1], 54:['toggle', 1], 53:['tap', 1]},
            {53:['tap', 0]}
]
layer_keys = [{'tab':'esc', 'esc':'tab'},
              {('a', 'b'):('z', 'v'), 'h':'left', 'j':'down', 'k':'up', ('ctrl', 'shift', 'l'):'right', 'c':('alt', 'shift', 'q')}
]

# convert layer_keys to key code versions (multi key binds must be tuples)
layer_key_codes = []
for layer in layer_keys:
    key_code_dict = {}
    for default_key, remap_key in layer.items():
        if type(default_key) is tuple:
            default_key_bind_list = []
            for key in default_key:
                key = keyboard.key_to_scan_codes(key)[0]
                default_key_bind_list.append(key)
            default_key = tuple(default_key_bind_list)
        else:
            default_key = keyboard.key_to_scan_codes(default_key)[0]

        if type(remap_key) is tuple:
            remap_key_bind_list = []
            for key in remap_key:
                key = keyboard.key_to_scan_codes(key)[0]
                remap_key_bind_list.append(key)
            remap_key = tuple(remap_key_bind_list)
        else:
            remap_key = keyboard.key_to_scan_codes(remap_key)[0]

        key_code_dict[default_key] = remap_key
    layer_key_codes.append(key_code_dict.copy())
print(layer_key_codes)


def first_press(last_key, key):
    if last_key.event_type == 'down' and last_key.scan_code == key.scan_code:
        return False
    else:
        return True

def key_code_bind_list(key_binds):
    bind_list = []
    for bind in key_binds:
        if type(bind) is tuple:
            for key in bind:
                bind_list.append(key)
        else:
            bind_list.append(bind)
    return bind_list

def detect_hotkey():
    for hotkey in layer_key_codes[layer_state].keys():
        print(hotkey)
        if keyboard.is_pressed(hotkey):
            print(f"hotkey: {hotkey}")
            return hotkey

layer_state = 0
old_layer_state = 0
momentary_key = None
momentary_layer = None
toggle_key = None
toggle_layer = None

last_key = None

def callback(key):
    global layer_state
    global old_layer_state
    
    global momentary_key
    global momentary_layer

    global toggle_key
    global toggle_layer

    global mod_keys
    global last_key
    global layer_keys

    global key_fallback

    global layer_key_codes

    layer_mod_keys = mod_keys[layer_state]

    hotkey_pressed = detect_hotkey()
    print(f"hotkey_pressed {hotkey_pressed}")

    if key.scan_code == momentary_key and key.event_type == 'up' and layer_state == momentary_layer:
        print(f"Momentary reverting to layer: {old_layer_state}")
        layer_state = old_layer_state
        momentary_key = None
        momentary_layer = None

    # Doesnt work with rshift as it sends 2 scan codes
    elif key.scan_code == toggle_key and key.event_type == 'down' and first_press(last_key, key) and layer_state == toggle_layer:
        print(f"Toggle reverting to layer: {old_layer_state}")
        layer_state = old_layer_state
        toggle_key = None
        toggle_layer = None
    
    elif key.scan_code in layer_mod_keys.keys():
        # momentary/tap
        mod_key_type = layer_mod_keys[key.scan_code][0]
        # layer mod key activates
        mod_key_layer = layer_mod_keys[key.scan_code][1]

        # Momentary
        if mod_key_type == 'momentary':
            if key.event_type == 'down' and first_press(last_key, key):
                # only save the old layer state if key is pressed for the first time
                old_layer_state = layer_state
                momentary_key = key.scan_code
                momentary_layer = mod_key_layer
                layer_state = mod_key_layer
                print(f"Momentary switching to layer: {layer_state}")
                print(f"Momentary original layer: {old_layer_state}")
        
        # Toggle
        elif mod_key_type == 'toggle':
            if key.event_type == 'down' and first_press(last_key, key):
                old_layer_state = layer_state
                toggle_key = key.scan_code
                toggle_layer = mod_key_layer
                layer_state = mod_key_layer
                print(f"Toggle switching to layer: {layer_state}")
                print(f"Toggle original layer: {old_layer_state}")

        # Tap
        elif mod_key_type == 'tap':
            if key.event_type == 'down' and first_press(last_key, key):
                layer_state = mod_key_layer
                print(f"Tap switching to layer: {layer_state}")

    # KEY BINDS SECTION
    # check if pressed key code is in the layer_key_codes dictionaries keys for the current layer
    elif hotkey_pressed and key.event_type == 'down':
        print(f"Releasing hotkey: {hotkey_pressed}")
        keyboard.release(hotkey_pressed)
        print(f"activating: {layer_key_codes[layer_state][hotkey_pressed]}")
        keyboard.send(layer_key_codes[layer_state][hotkey_pressed])

    # press default keys if key fallback is enabled for layer
    elif key_fallback[layer_state]:
        if key.event_type == 'down':
            keyboard.press(key.scan_code)
        else:
            keyboard.release(key.scan_code)

    # stores last key event as last_key
    last_key = key
    print(key, key.scan_code, key.event_type)


system = platform.system()
if system == 'Linux':
    kb_id = disable_x_input()

# Activates keyboard monkey patch
keyboard._KeyboardListener.direct_callback = custom_direct_callback

keyboard.hook(callback, suppress=True)

try:
    keyboard.wait()
except KeyboardInterrupt:
    # re-enable keyboard on exit
    if system == 'Linux':
        subprocess.run(['xinput', '--enable', kb_id])
        print("Enabling id={}".format(kb_id))
