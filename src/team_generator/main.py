from src.champions import get_chamption_data
import random
import logging

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("team_generator")


def get_champion_image(champion_name):
    return f"https://ddragon.leagueoflegends.com/cdn/14.22.1/img/champion/{champion_name}.png"


def generate_team(nicknames):
    players = len(nicknames) // 2

    if players is None:
        if nicknames % 2 != 0:
            raise ValueError("The number of players must be even")

    champions = get_chamption_data()

    champions_names = list(champions.keys())
    champions_qnt = len(champions_names)

    red_team_champion_names = []
    blue_team_champion_names = []

    control_map = {}
    for i in range(players * 2):
        while True:
            choice_blue = random.randint(0, champions_qnt - 1)
            if control_map.get(choice_blue, None) is None:
                control_map[choice_blue] = True
                break

        while True:
            choice_red = random.randint(0, champions_qnt - 1)
            if control_map.get(choice_red, None) is None:
                control_map[choice_red] = True
                break


        red_team_champion_names.append(champions_names[choice_red])
        blue_team_champion_names.append(champions_names[choice_blue])


    red_champions = [{"image": get_champion_image(i), "name": i} for i in red_team_champion_names]

    blue_champions = [{"image": get_champion_image(i), "name": i} for i in blue_team_champion_names]

    control_map = {}

    red_team_players = []
    blue_team_players = []
    for i in range(players):
        while True:
            choice_blue = random.randint(0, len(nicknames) - 1)
            if control_map.get(choice_blue, None) is None:
                control_map[choice_blue] = True
                break

        while True:
            choice_red = random.randint(0, len(nicknames) - 1)
            if control_map.get(choice_red, None) is None:
                control_map[choice_red] = True
                break

        red_team_players.append(nicknames[choice_red])
        blue_team_players.append(nicknames[choice_blue])

    return {
        'red_team': {"champions" : red_champions, "players": red_team_players},
        'blue_team': {"champions" : blue_champions, "players": blue_team_players},
    }


if __name__ == '__main__':
    print(generate_team(["jonata", "wanis", "loui", "jp", "arthur", "tales", "karen"]))
