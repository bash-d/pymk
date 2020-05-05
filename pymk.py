#!/usr/bin/python3

import platform
import keyboard
import subprocess
import re
import unicodedata
import configparser

def modify_listener():
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
    
        """
        MODIFIED PART
        captures keyboard events even if a hook is suppressing
        
        if the hook is not suppressing some issues happen because of hotkey recursion
        """
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

    # Activates keyboard monkey patch
    keyboard._KeyboardListener.direct_callback = custom_direct_callback

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
#key_fallback = [True,
#                False,
#]

"""
mod keys must be keycodes to differentiate right and left duplicate keys (e.g. rshift/lshift)

probably cant use keys names that correspond to specific keycodes because keycodes differ between OS

config file prob has to use keycodes and only UI will be able to use key names instead
"""

#modkeys = [{58:['momentary', 1], 54:['toggle', 1], 53:['tap', 1]},
#            {53:['tap', 0]}
#]
#hotkeys = [{'tab':'esc', 'esc':'tab'},
#           {('a', 'b'):('z', 'v'), 'h':'left', 'j':'down', 'k':'up', ('ctrl', 'shift', 'l'):'right', 'c':('alt', 'shift', 'q')}
#]

#hotkeys = [{(15,): (1,), (1,): (15,)}, {(35,): (105,), (36,): (108,), (37,): (103,), (38,): (106,), (46,): (56, 42, 16), (30, 48): (44, 47)}]

def parse_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    
    key_fallback = []
    modkeys = []
    hotkeys = []
    for layer in config.sections():
        # key fallback
        key_fallback.append(config[layer]['key_fallback'])

        # modkeys
        config_modkeys = config[layer]['modkeys'].strip().split('\n')
        layer_modkeys = {}
    
        for modkey in config_modkeys:
            modkey = modkey.split('=')
            map_key = modkey[0].split(',')
            map_key = [x.strip(' ') for x in map_key]
            map_key_list = []

            for key in map_key:
                try:
                    key = keyboard.key_to_scan_codes(key)[0]
                except: 
                    key = keyboard.key_to_scan_codes(int(key))[0]
                print(repr(key))
                map_key_list.append(key)
            map_key = tuple(map_key_list)
            print(map_key)
            
            key_action = modkey[1][1:].split(',')
            key_action[1] = int(key_action[1])
            layer_modkeys[map_key] = tuple(key_action)
        modkeys.append(layer_modkeys)

        # hotkeys    
        config_hotkeys = config[layer]['hotkeys'].strip().split('\n')
        layer_hotkeys = {}
    
        for hotkey in config_hotkeys:
            hotkey = hotkey.split('=')
            map_key = hotkey[0].split(',')
            map_key = [x.strip(' ') for x in map_key]
            map_key_list = []
    
            remap_key = hotkey[1].split(',')
            remap_key = [x.strip(' ') for x in remap_key]
            remap_key_list = []
    
            for key in map_key:
                key = keyboard.key_to_scan_codes(key)[0]
                map_key_list.append(key)
            map_key = tuple(map_key_list)
    
            for key in remap_key:
                key = keyboard.key_to_scan_codes(key)[0]
                remap_key_list.append(key)
            remap_key = tuple(remap_key_list)
            remap_key = keyboard.key_to_scan_codes(remap_key)
            layer_hotkeys[map_key] = remap_key
    
        hotkeys.append(layer_hotkeys)
    return key_fallback, modkeys, hotkeys

def first_press(last_key, key):
    if last_key.event_type == 'down' and last_key.scan_code == key.scan_code:
        return False
    else:
        return True

def first_multipress(last_multikey, multikey):
    if last_key.event_type == 'down' and last_multikey == multikey:
        return False
    else:
        return True

# currently not in use
# converts tuples in list into more list values
def key_code_bind_list(key_binds):
    bind_list = []
    for bind in key_binds:
        if type(bind) is tuple:
            for key in bind:
                bind_list.append(key)
        else:
            bind_list.append(bind)
    return bind_list

def detect_multikey(hotkeys):
    for hotkey in hotkeys[layer].keys():
        if keyboard.is_pressed(hotkey):
            print(f"hotkey: {hotkey}")
            return hotkey

layer = 0
last_layer = 0
last_key = None
last_multikey = ()
momentary_key = None
momentary_layer = None
toggle_key = None
toggle_layer = None

def callback(key):
    global layer
    global last_layer
    global last_key
    global last_multikey
    global modkeys
    global momentary_key
    global momentary_layer
    global toggle_key
    global toggle_layer
    global key_fallback
    global hotkeys

    print(f"keyfallback: {key_fallback[layer]}")
    layer_modkeys = modkeys[layer]
    hotkey_pressed = detect_multikey(hotkeys)

    multikey_list = (tuple(keyboard._pressed_events.keys()))
    #if len(multikey) > 0:
    #    for key in multikey:
    #        # contains scan code and event type for each keyboard event {33: 'down'}
    #        multikey_list[key.scan_code] = key.event_type
    #        multikey_list = tuple(multikey_list.keys())
    #        event_types = tuple(multikey_list.values())

    print(f"codes: {multikey_list}, {last_multikey}")
    # detect momentary release to rever to previous layer
    if layer == momentary_layer and not all(x in multikey_list for x in momentary_key):
        print(f"Momentary reverting to layer: {last_layer}")
        print(all(x in multikey_list for x in momentary_key))
        layer = last_layer
        momentary_key = None
        momentary_layer = None

    # Doesnt work with rshift as it sends 2 scan codes
    # detect when toggle key is pressed again to revert to previous layer
    elif layer == toggle_layer and multikey_list == toggle_key and last_multikey != multikey_list:
        print(f"Toggle reverting to layer: {last_layer}")
        layer = last_layer
        toggle_key = None
        toggle_layer = None
    
    elif detect_multikey(modkeys):
        modkey = multikey_list
        # momentary/tap
        modkey_type = layer_modkeys[modkey][0]
        # layer mod key activates
        modkey_layer = layer_modkeys[modkey][1]
        print(f"MODKEY:{modkey_layer}, {modkey_type}")

        # Momentary
        if modkey_type == 'momentary':
            if key.event_type == 'down' and first_press(last_key, key):
                # only save the old layer state if key is pressed for the first time
                last_layer = layer
                momentary_key = modkey
                momentary_layer = modkey_layer
                layer = modkey_layer
                print(f"Momentary switching to layer: {layer}")
                print(f"Momentary original layer: {last_layer}")
        
        # Toggle
        elif modkey_type == 'toggle':
            if key.event_type == 'down' and first_press(last_key, key):
                last_layer = layer
                toggle_key = modkey
                toggle_layer = modkey_layer
                layer = modkey_layer
                print(f"Toggle switching to layer: {layer}")
                print(f"Toggle original layer: {last_layer}")

        # Tap
        elif modkey_type == 'tap':
            if key.event_type == 'down' and first_press(last_key, key):
                layer = modkey_layer
                print(f"Tap switching to layer: {layer}")
        
    #elif key.scan_code in layer_modkeys.keys():
    #    # momentary/tap
    #    modkey_type = layer_modkeys[key.scan_code][0]
    #    # layer mod key activates
    #    modkey_layer = layer_modkeys[key.scan_code][1]

    #    # Momentary
    #    if modkey_type == 'momentary':
    #        if key.event_type == 'down' and first_press(last_key, key):
    #            # only save the old layer state if key is pressed for the first time
    #            last_layer = layer
    #            momentary_key = key.scan_code
    #            momentary_layer = modkey_layer
    #            layer = modkey_layer
    #            print(f"Momentary switching to layer: {layer}")
    #            print(f"Momentary original layer: {last_layer}")
    #    
    #    # Toggle
    #    elif modkey_type == 'toggle':
    #        if key.event_type == 'down' and first_press(last_key, key):
    #            last_layer = layer
    #            toggle_key = key.scan_code
    #            toggle_layer = modkey_layer
    #            layer = modkey_layer
    #            print(f"Toggle switching to layer: {layer}")
    #            print(f"Toggle original layer: {last_layer}")

    #    # Tap
    #    elif modkey_type == 'tap':
    #        if key.event_type == 'down' and first_press(last_key, key):
    #            layer = modkey_layer
    #            print(f"Tap switching to layer: {layer}")

    # KEY BINDS SECTION
    # check if pressed key code is in the hotkeys dictionaries keys for the current layer
    elif hotkey_pressed and key.event_type == 'down':
        print(f"Releasing hotkey: {hotkey_pressed}")
        # release hotkeys mapped keys to ensure they are not pressed down when the remapped keys are pressed
        keyboard.release(hotkey_pressed)
        print(f"activating: {hotkeys[layer][hotkey_pressed]}")
        keyboard.send(hotkeys[layer][hotkey_pressed])

    # press default keys if key fallback is enabled for layer
    elif key_fallback[layer]:
        if key.event_type == 'down':
            keyboard.press(key.scan_code)
        else:
            keyboard.release(key.scan_code)

    # stores last key event as last_key
    last_multikey = multikey_list
    last_key = key
    #print(key, key.scan_code, key.event_type)


key_fallback, modkeys, hotkeys = parse_config('config.ini')
system = platform.system()
if system == 'Linux':
    kb_id = disable_x_input()
    keyboard.hook(callback, suppress=False)
elif system == 'Windows':
    modify_listener()
    keyboard.hook(callback, suppress=True)

try:
    keyboard.wait()
except KeyboardInterrupt:
    # re-enable keyboard on exit
    if system == 'Linux':
        subprocess.run(['xinput', '--enable', kb_id])
        print("Enabling id={}".format(kb_id))
