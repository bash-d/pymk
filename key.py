#!/usr/bin/python3

import platform
import keyboard
import subprocess
import re
import unicodedata

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
default_keys = [False,
               True,
]

mod_keys = [{58:['momentary', 1], 54:['toggle', 1], 53:['tap', 1]},
            {53:['tap', 0]}
]
layer_keys = [{'tab':'esc', 'esc':'tab'},
              {'h':'left', 'j':'down', 'k':'up', 'l':'right', 'c':'alt+shift+q'}
]

# convert layer_keys to key code version except for multi key binds
layer_key_codes = []
for layer in layer_keys:
    key_code_dict = {}
    for default_key, remap_key in layer.items():
        try:
            default_key = keyboard.key_to_scan_codes(default_key)[0]
            remap_key = keyboard.key_to_scan_codes(remap_key)[0]
        except:
            pass
        key_code_dict[default_key] = remap_key
    layer_key_codes.append(key_code_dict.copy())
print(layer_key_codes)

layer_state = 0
old_layer_state = 0
momentary_key = None
momentary_layer = None
toggle_key = None
toggle_layer = None

last_key = None
user_press = False

def first_press(last_key, key):
    if last_key.event_type == 'down' and last_key.scan_code == key.scan_code:
        return False
    else:
        return True

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

    global default_keys

    global user_press

    layer_mod_keys = mod_keys[layer_state]

    if key.scan_code == momentary_key and key.event_type == 'up' and layer_state == momentary_layer:
        print(f"Momentary reverting to layer: {old_layer_state}")
        layer_state = old_layer_state
        momentary_key = None
        momentary_layer = None

    # Doesnt work with rshift as it sends 2 scan codes
    #elif key.scan_code == toggle_key and key.event_type == 'down' and first_press(last_key, key) == True and layer_state == toggle_layer:
    #    print(toggle_key)
    #    print(f"TOGGLE GOING BACK TO: {old_layer_state}")
    #    layer_state = old_layer_state
    #    toggle_key = None
    #    toggle_layer = None
    
    elif key.scan_code in layer_mod_keys.keys():
        # momentary/tap
        mod_key_type = layer_mod_keys[key.scan_code][0]
        # layer mod key activates
        mod_key_layer = layer_mod_keys[key.scan_code][1]

        # Momentary
        if mod_key_type == 'momentary':
            if key.event_type == 'down':
                # only save the old layer state if key is pressed for the first time
                if first_press(last_key, key):
                    old_layer_state = layer_state

                momentary_key = key.scan_code
                momentary_layer = mod_key_layer
                layer_state = mod_key_layer
                print(f"Momentary switching to layer: {layer_state}")
                print(f"Momentary original layer: {old_layer_state}")
        
        ## Toggle
        #elif mod_key_type == 'toggle':
        #    if key.event_type == 'down':
        #        if first_press(last_key, key):
        #            old_layer_state = layer_state
        #        
        #            toggle_key = key.scan_code
        #            toggle_layer = mod_key_layer
        #            layer_state = mod_key_layer
        #            print(f"TOGGLE layer state: {layer_state}")
        #            print(f"TOGGLE OLD layer state: {old_layer_state}")


        # Tap
        elif mod_key_type == 'tap':
            if key.event_type == 'down' and first_press(last_key, key):
                layer_state = mod_key_layer
                print(f"Tap switching to layer: {layer_state}")

    # check if current layer has any user binds
    elif layer_state < len(layer_key_codes) and key.scan_code in layer_key_codes[layer_state] and user_press:

        # get all binds for current layer
        active_layer_keys = layer_key_codes[layer_state]

        # press user binds for layer
        if key.event_type == 'down':
            keyboard.press(active_layer_keys[key.scan_code])
            user_press = False 
        else:
            print("Keybind release")
            keyboard.release(active_layer_keys[key.scan_code])
            user_press = False 

    elif default_keys[layer_state] and not [value for ke, value in layer_key_codes[layer_state].items() if key.scan_code == ke or key.scan_code == value]:
        print(f"Broke: {key.scan_code}")
        print(f"Broke: {layer_key_codes[layer_state]}")
        print("Broke")
    elif key.event_type == 'down':
        keyboard.press(key.name)
        user_press = True
        #print("normal: {}".format(key))
    else:
        keyboard.release(key.name)
        user_press = True
        #print("normal: {}".format(key))

    # stores key event for last key press
    last_key = key
    print(key, key.scan_code, key.event_type)
    #print(f"User press: {user_press}")

system = platform.system()
if system == 'Linux':
    kb_id = disable_x_input()

keyboard.hook(callback, suppress=True)

try:
    keyboard.wait()
except KeyboardInterrupt:
    # re-enable keyboard on exit
    if system == 'Linux':
        subprocess.run(['xinput', '--enable', kb_id])
        print("Enabling id={}".format(kb_id))
