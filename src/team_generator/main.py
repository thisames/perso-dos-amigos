from src.champions import get_chamption_data
import random
import logging

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("team_generator")


def get_champion_image(champion_name):
    return f"https://ddragon.leagueoflegends.com/cdn/14.22.1/img/champion/{champion_name}.png"


def generate_team(players=5):
    champions = get_chamption_data()

    champions_names = list(champions.keys())
    champions_qnt = len(champions_names)

    red_team_names = []
    blue_team_names = []

    for i in range(players * 2):
        choice_blue = random.randint(0, champions_qnt - 1)
        choice_red = random.randint(0, champions_qnt - 1)

        while champions_names[choice_blue] is None:
            choice_blue = random.randint(0, champions_qnt - 1)

        while champions_names[choice_red] is None:
            choice_red = random.randint(0, champions_qnt - 1)

        red_team_names.append(champions_names[choice_red])
        blue_team_names.append(champions_names[choice_blue])
        champions_names[choice_blue] = None
        champions_names[choice_red] = None

    red_team = [{"image": get_champion_image(i), "name": i} for i in red_team_names]

    blue_team = [{"image": get_champion_image(i), "name": i} for i in blue_team_names]

    return {
        'red_team': red_team,
        'blue_team': blue_team,
    }


if __name__ == '__main__':
    generate_team()
