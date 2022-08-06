"""Idealista Explorer

Use the idealista.com API to run queries
(c) 2017 Marcelo Novaes
"""

import argparse
import json
import os
import time
import requests
from requests.auth import HTTPBasicAuth

from loguru import logger
from dotenv import load_dotenv


# logger.add('logfile', format="{time:YYYY-MM-DD HH:mm:ss} {level} {message}", colorize=True)
# Sets the name to look for enviroment variables
load_dotenv()
ENV_API_KEY = "IDEALISTA_API_KEY"
ENV_API_SECRET = "IDEALISTA_API_SECRET"


def get_oauth_token(key, secret):
    """Gets oauth2 token from the API Key and Secret provided by idealista
    """
    oauth_url = "https://api.idealista.com/oauth/token"
    payload = {"grant_type": "client_credentials"}
    r = requests.post(oauth_url,
                      auth=HTTPBasicAuth(key, secret),
                      data=payload)
    token_response = json.loads(r.text)
    try:
        token_value = token_response["access_token"]
    except KeyError:
        logger.error(f"No access_token found in response. Is the proper API token provided?")
        exit()
    logger.debug(f"Token: {token_value}")
    return token_value


def search_api(url, token):
    """Runs a search using the API and a token
    """
    headers = {"Authorization": "Bearer " + token}
    r = requests.post(url,
                      headers=headers)
    return r.text


def parse_args():
    parser = argparse.ArgumentParser(description="Arguments for Idealista API")
    parser.add_argument("url")
    args = parser.parse_args()
    logger.debug("URL provided: {}".format(args.url))
    return args.url


def get_environment_variables():
    api_key = os.environ.get(ENV_API_KEY)
    if api_key:
        logger.debug("Idealista API key loaded from environment: " + api_key)
    else:
        logger.error("No Idealista API key found as environment variable " + ENV_API_KEY)
    api_secret = os.environ.get(ENV_API_SECRET)
    if api_secret:
        logger.debug("Idealista API secret loaded from environment: " + api_secret)
    else:
        logger.error("No Idealista API secret found as environment variable " + ENV_API_SECRET)
    return api_key, api_secret


def request_idealista(url_value):
    api_key, api_secret = get_environment_variables()
    token_value = get_oauth_token(api_key, api_secret)

    search_json = search_api(url_value, token_value)
    search_response = json.loads(search_json)
    search_pretty = json.dumps(search_response, indent=4, sort_keys=True)
    logger.debug('Got response from Idealista API.')

    filename = "data/idealista_json_" + time.strftime("%Y-%m-%d_%H-%M") + ".json"
    with open(filename, 'w') as export:
        json.dump(search_pretty, export)
        logger.debug(f'Wrote response to file: {filename}')


if __name__ == "__main__":
    url_value = parse_args()
    request_idealista(url_value)
