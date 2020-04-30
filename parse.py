#!/usr/bin/python3
import configparser
import keyboard

config = configparser.ConfigParser()
config.read('config.ini')

modkeys = []
hotkeys = []
for layer in config.sections():
    config_modkeys = config[layer]['modkeys'].strip().split('\n')
    layer_modkeys = {}

    for key in config_modkeys:
        key = key.split('=')
        key_code = int(key[0][:-1])
        key_action = key[1][1:].split(',')
        key_action[1] = int(key_action[1])
        layer_modkeys[key_code] = tuple(key_action)
    modkeys.append(layer_modkeys)

    config_hotkeys = config[layer]['hotkeys'].strip().split('\n')
    layer_hotkeys = {}

    for key in config_hotkeys:
        key = key.split('=')
        map_key = key[0].split(',')
        map_key = [key.strip(' ') for key in map_key]
        map_key_list = []

        remap_key = key[1].split(',')
        remap_key = [key.strip(' ') for key in remap_key]
        remap_key_list = []

        for key in map_key:
            key = keyboard.key_to_scan_codes(key)[0]
            map_key_list.append(key)
        map_key = tuple(map_key_list)
        print(f"map: {map_key}")

        for key in remap_key:
            key = keyboard.key_to_scan_codes(key)[0]
            remap_key_list.append(key)
        remap_key = tuple(remap_key_list)
        remap_key = keyboard.key_to_scan_codes(remap_key)
        print(f"remap: {remap_key}")
        layer_hotkeys[map_key] = remap_key

    hotkeys.append(layer_hotkeys)

print(hotkeys)
print(modkeys)
