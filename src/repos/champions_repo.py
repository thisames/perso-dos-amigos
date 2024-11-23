from queue import Queue, Empty
from threading import Thread

import requests
import logging

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("champions")

BASE_API_URL = "https://ddragon.leagueoflegends.com"


def download_champion_image(version, name):
    url = f"{BASE_API_URL}/cdn/{version}/img/champion/{name}.png"
    response = requests.get(url)
    return response.content


def get_last_league_version():
    url = f"{BASE_API_URL}/api/versions.json"

    response = requests.get(url)

    if response.status_code == 200:
        return response.json()[0]
    else:
        logger.error("Error getting last league version: %s", response.text)
        raise Exception(f"Error getting last league version")


class ImageDict(dict):
    def __init__(self):
        super().__init__()
        self.version = get_last_league_version()
        self.__load_champions()

    def __load_champions(self):
        url = f"{BASE_API_URL}/cdn/{self.version}/data/en_US/champion.json"

        response = requests.get(url)

        logger.info("Downloading champions list")
        if response.status_code == 200:
            champions = response.json()['data']

            q = Queue()

            def __fetch_champion(version):
                finished = False
                while not finished:
                    try:
                        champion_name = q.get(block=False)
                        logger.info(f'Downloading champion {champion_name}')
                        image = download_champion_image(version, champion_name)
                        self[champion_name] = {
                            "name": champions[champion_name]["name"],
                            "image": image
                        }
                        q.task_done()
                    except Empty:
                        finished = True

            for champion in champions:
                q.put(champion)

            for i in range(10):
                t = Thread(target=__fetch_champion, daemon=True, args=(self.version,))
                t.start()

            q.join()

            logger.info("Download finished")

        else:
            logger.error("Error getting champions list: %s", response.text)
            raise Exception(f"Error getting champions list")

