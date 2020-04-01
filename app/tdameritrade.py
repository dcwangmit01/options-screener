#!/usr/bin/env python3

import time
from os import path
import requests_cache

import tdameritrade as td
from tdameritrade import auth as tdauth

from app.utils import YamlUtils

# SETTINGS
CONFIG_FILE = path.expanduser('~/.tdameritrade')
SECONDS_TO_CACHE = 180  # seconds


class TDAmeritrade(object):
    config = None

    def __init__(self):
        # Create the requests cache to reduce web traffic
        self.session = requests_cache.CachedSession(cache_name='cache', backend='sqlite', expire_after=SECONDS_TO_CACHE)
        self.initConfig()
        self.saveConfig()

    def initConfig(self):
        # Read the configuration, or create a new configuration
        if path.exists(CONFIG_FILE):
            self.config = YamlUtils.yaml_dict_from_file(CONFIG_FILE)
        else:
            self.config = {
                'tda_user': '',
                'tda_pass': '',
                'client_id': '',
                'redirect_uri': '',
                '_oauth2': {
                    # The following come back from the authorization reponses
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

        # Ensure all parts of the configuration are filled in
        if self.config['tda_user'] == '':
            self.config['tda_user'] = input('Please enter your tdameritrade.com Username:\n: ')
        if self.config['tda_pass'] == '':
            self.config['tda_pass'] = input('Please enter your tdameritrade.com Password:\n: ')
        if self.config['client_id'] == '':
            self.config['client_id'] = input('Please enter your developer.tdameritrade Application Consumer Key\n' +
                                             '  From https://developer.tdameritrade.com/user/me/apps:\n: ')
        if self.config['redirect_uri'] == '':
            self.config['redirect_uri'] = input('Please enter your developer.tdameritrade Application Redirect URI\n' +
                                                '  From https://developer.tdameritrade.com/user/me/apps:\n: ')

    def saveConfig(self):
        # Write the configuration back to file
        if YamlUtils.yaml_dict_to_string(self.config) != YamlUtils.yaml_dict_to_string(
                YamlUtils.yaml_dict_from_file(CONFIG_FILE)):
            print(f"Updating configuration file at {CONFIG_FILE}")
            YamlUtils.yaml_dict_to_file(self.config, CONFIG_FILE)

    def ensureAuth(self):
        # Handle Authentication/Authorization
        now = int(time.time())
        if (self.config['_oauth2']['access_token_timestamp'] == ''):
            print("New Authentication Required: Empty Auth State")
            self.config['_oauth2'].update(
                tdauth.authentication(client_id=self.config['client_id'],
                                      redirect_uri=self.config['redirect_uri'],
                                      tdauser=self.config['tda_user'],
                                      tdapass=self.config['tda_pass']))
            self.config['_oauth2']['access_token_timestamp'] = now
            self.config['_oauth2']['refresh_token_timestamp'] = now
        elif (now > int(self.config['_oauth2']['refresh_token_timestamp']) +
              int(self.config['_oauth2']['refresh_token_expires_in']) - (24 * 60 * 60)):
            print("New Authentication Required: Access Token And Refresh Token Expired")
            self.config['_oauth2'].update(
                tdauth.authentication(client_id=self.config['client_id'],
                                      redirect_uri=self.config['redirect_uri'],
                                      tdauser=self.config['tda_user'],
                                      tdapass=self.config['tda_pass']))
            self.config['_oauth2']['access_token_timestamp'] = now
            self.config['_oauth2']['refresh_token_timestamp'] = now
        elif (now > int(self.config['_oauth2']['access_token_timestamp']) + int(self.config['_oauth2']['expires_in']) -
              (5 * 60)):
            print("Refresh Authentication Required: Access Token Expired, Exchanging Valid Refresh Token")
            self.config['_oauth2'].update(
                tdauth.refresh_token(refresh_token=self.config['_oauth2']['refresh_token'],
                                     client_id=self.config['client_id']))
            self.config['_oauth2']['access_token_timestamp'] = now
        else:
            print("Current Authentication Tokens Valid")

        self.saveConfig()

    def getClient(self):
        self.ensureAuth()

        # Return the client
        return td.TDClient(access_token=self.config['_oauth2']['access_token'], accountIds=None)
