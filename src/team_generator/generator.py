import random
import logging

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("team_generator")


def generate_team(nicknames, champions):
    players = len(nicknames) // 2

    if players is None:
        if nicknames % 2 != 0:
            raise ValueError("The number of players must be even")

    red_team_champion_names = []
    blue_team_champion_names = []

    for i in range(players * 2):
        choice_blue = random.randint(0, len(champions) - 1)
        blue_team_champion_names.append(champions[choice_blue])
        del champions[choice_blue]

        choice_red = random.randint(0, len(champions) - 1)
        red_team_champion_names.append(champions[choice_red])
        del champions[choice_red]

    random.shuffle(nicknames)

    red_team_players = nicknames[:len(nicknames) // 2]
    blue_team_players = nicknames[len(nicknames) // 2:]

    return {
        'red_team': {"champions": red_team_champion_names, "players": red_team_players},
        'blue_team': {"champions": blue_team_champion_names, "players": blue_team_players},
    }
