#!/usr/bin/python3
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

final = []
for layer in config.sections():
    mod_keys = config[layer]['mod_keys'].strip().split('\n')
    layer_mod_keys = {}
    for key in mod_keys:
        key = key.split('=')
        key_code = int(key[0][:-1])
        key_action = key[1][1:].split(',')
        key_action[1] = int(key_action[1])
        layer_mod_keys[key_code] = tuple(key_action)
    final.append(layer_mod_keys)
print(final)
