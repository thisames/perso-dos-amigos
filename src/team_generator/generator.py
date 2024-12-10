import random
import logging

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("team_generator")


def generate_team(players, champions, fixed_teams):
    if fixed_teams:
        team_size = len(players.get("A"))
        red_team_players, blue_team_players = (
            players.get("A"), players.get("B")
        ) if random.randint(0, 1) else (
            players.get("B"), players.get("A")
        )
    else:
        team_size = len(players) // 2

        if team_size is None:
            if players % 2 != 0:
                raise ValueError("The number of players must be even")

        random.shuffle(players)

        red_team_players = players[:len(players) // 2]
        blue_team_players = players[len(players) // 2:]

    red_team_champion_names = []
    blue_team_champion_names = []

    for i in range(team_size * 2):
        choice_blue = random.randint(0, len(champions) - 1)
        blue_team_champion_names.append(champions[choice_blue])
        del champions[choice_blue]

        choice_red = random.randint(0, len(champions) - 1)
        red_team_champion_names.append(champions[choice_red])
        del champions[choice_red]

    return {
        "red_team": {"champions": red_team_champion_names, "players": red_team_players},
        "blue_team": {"champions": blue_team_champion_names, "players": blue_team_players},
    }
