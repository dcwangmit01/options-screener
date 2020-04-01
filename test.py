#!/usr/bin/env python3

import time
from os import path

import tdameritrade as td
from tdameritrade import auth as tdauth

from app.utils import YamlUtils

CONFIG_FILE = path.expanduser('~/.tdameritrade')

# Read the configuration, or create a new configuration
config = {}
if path.exists(CONFIG_FILE):
    config = YamlUtils.yaml_dict_from_file(CONFIG_FILE)
else:
    config = {
        'tda_user': '',
        'tda_pass': '',
        'client_id': '',
        'redirect_uri': '',
        '_oauth2': {
            # The following comes back in the initial authorization
            'access_token': '',
            'refresh_token': '',
            'scope': '',
            'expires_in': '',
            'refresh_token_expires_in': '',
            'token_type': '',
            # The following are fields added to track expiration
            'access_token_timestamp': '',
            'refresh_token_timestamp': '',
        }
    }
    YamlUtils.yaml_dict_to_file(config, CONFIG_FILE)
    print(f"Created configuration file at {CONFIG_FILE}")

# Ensure all parts of the configuration are filled in
if config['tda_user'] == '':
    config['tda_user'] = input('Please enter your tdameritrade.com Username:\n: ')
if config['tda_pass'] == '':
    config['tda_pass'] = input('Please enter your tdameritrade.com Password:\n: ')
if config['client_id'] == '':
    config['client_id'] = input('Please enter your developer.tdameritrade Application Consumer Key\n' +
                                '  From https://developer.tdameritrade.com/user/me/apps:\n: ')
if config['redirect_uri'] == '':
    config['redirect_uri'] = input('Please enter your developer.tdameritrade Application Redirect URI\n' +
                                   '  From https://developer.tdameritrade.com/user/me/apps:\n: ')

# Handle Authentication/Authorization
now = int(time.time())
if (config['_oauth2']['access_token_timestamp'] == ''):
    print("New Authentication Required: Empty Auth State")
    config['_oauth2'].update(
        tdauth.authentication(client_id=config['client_id'],
                              redirect_uri=config['redirect_uri'],
                              tdauser=config['tda_user'],
                              tdapass=config['tda_pass']))
    config['_oauth2']['access_token_timestamp'] = now
    config['_oauth2']['refresh_token_timestamp'] = now
elif (now > int(config['_oauth2']['refresh_token_timestamp']) + int(config['_oauth2']['refresh_token_expires_in']) -
      (24 * 60 * 60)):
    print("New Authentication Required: Access Token And Refresh Token Expired")
    config['_oauth2'].update(
        tdauth.authentication(client_id=config['client_id'],
                              redirect_uri=config['redirect_uri'],
                              tdauser=config['tda_user'],
                              tdapass=config['tda_pass']))
    config['_oauth2']['access_token_timestamp'] = now
    config['_oauth2']['refresh_token_timestamp'] = now
elif (now > int(config['_oauth2']['access_token_timestamp']) + int(config['_oauth2']['expires_in']) - (5 * 60)):
    print("Refresh Authentication Required: Access Token Expired, Exchanging Valid Refresh Token")
    config['_oauth2'].update(
        tdauth.refresh_token(refresh_token=config['_oauth2']['refresh_token'], client_id=config['client_id']))
    config['_oauth2']['access_token_timestamp'] = now
else:
    print("Current Authentication Tokens Valid")

# Write back to the configuration file
if YamlUtils.yaml_dict_to_string(config) != YamlUtils.yaml_dict_to_string(YamlUtils.yaml_dict_from_file(CONFIG_FILE)):
    print(f"Updating configuration file at {CONFIG_FILE}")
    YamlUtils.yaml_dict_to_file(config, CONFIG_FILE)

#
c = td.TDClient(access_token=config['_oauth2']['access_token'], accountIds=None)

df = c.optionsDF('SPY')

import ipdb
ipdb.set_trace()
