import json

import requests
import logging

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("champions")


def get_last_league_version():
    url = "https://ddragon.leagueoflegends.com/api/versions.json"

    response = requests.get(url)

    if response.status_code == 200:
        return response.json()[0]
    else:
        logger.error("Error getting last league version: %s", response.text)
        raise Exception(f"Error getting last league version")


def get_chamption_data():
    last_ddragon_version = get_last_league_version()
    champion_file = f"/tmp/champions-{last_ddragon_version}.json"

    try:
        with open(champion_file, "r") as f:
            logger.info("Using cached champions list")
            return json.load(f)
    except FileNotFoundError:
        pass

    url = f"https://ddragon.leagueoflegends.com/cdn/{last_ddragon_version}/data/en_US/champion.json"

    response = requests.get(url)
    logger.info("Downloading champions list")
    if response.status_code == 200:
        champions = response.json()

        with open(champion_file, "w") as f:
            f.write(json.dumps(champions["data"]))
            f.close()
            return champions["data"]
    else:
        logger.error("Error getting champions list: %s", response.text)
        raise Exception(f"Error getting champions list")
