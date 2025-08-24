import random
import logging
import repos.firebase_repo as repo

logging.basicConfig(format='%(levelname)s %(name)s %(asctime)s: %(message)s', level=logging.INFO)
logger = logging.getLogger("team_generator")


async def calculate_player_ratings(players, all_seasons=False):
    """
    Calculate player ratings based on their match history.
    Returns a dict with player_id -> rating
    """
    if all_seasons:
        # Get matches from all seasons by not filtering by season
        matches = await repo.get_finished_matches(0, None)
    else:
        season_ref = await repo.get_last_season()
        matches = await repo.get_finished_matches(0, season_ref)

    # Initialize stats for all players
    stats = {}
    for player in players:
        player_id = player.id if hasattr(player, 'id') else player
        stats[player_id] = {"wins": 0, "losses": 0, "games": 0}

    # Calculate stats from matches
    for match in matches:
        winning_team = match.get("blue_team") if match.get("result") == "BLUE" else match.get("red_team")
        losing_team = match.get("red_team") if match.get("result") == "BLUE" else match.get("blue_team")

        for player_id in winning_team["players"]:
            if player_id in stats:
                stats[player_id]["wins"] += 1
                stats[player_id]["games"] += 1

        for player_id in losing_team["players"]:
            if player_id in stats:
                stats[player_id]["losses"] += 1
                stats[player_id]["games"] += 1

    # Calculate dynamic confidence threshold based on match distribution
    total_matches = len(matches)
    games_played = [stat["games"] for stat in stats.values() if stat["games"] > 0]

    if not games_played:
        # No games played by anyone, use baseline for all
        confidence_threshold = 1
        logger.info("No games found, using baseline ratings")
    else:
        # Calculate statistics about game distribution
        avg_games = sum(games_played) / len(games_played)
        max_games = max(games_played)

        # Dynamic threshold: 25% of average games or minimum 3, maximum 15
        confidence_threshold = max(3, min(15, int(avg_games * 0.25)))

        logger.info(f"Match analysis: Total={total_matches}, Avg games/player={avg_games:.1f}, Max games={max_games}, Confidence threshold={confidence_threshold}")

    # Calculate rating for each player using confidence-weighted system
    ratings = {}
    baseline_winrate = 0.5  # 50% baseline

    for player in players:
        player_id = player.id if hasattr(player, 'id') else player
        stat = stats[player_id]

        if stat["games"] == 0:
            # No games played, use baseline
            rating = baseline_winrate * 100
        else:
            # Calculate raw winrate
            raw_winrate = stat["wins"] / stat["games"]

            # Calculate confidence factor (0 to 1)
            # Players with fewer games get pulled toward the baseline
            confidence = min(stat["games"] / confidence_threshold, 1.0)

            # Weighted average between raw winrate and baseline
            # More games = more weight to raw winrate
            # Fewer games = more weight to baseline (regression to mean)
            adjusted_winrate = (confidence * raw_winrate) + ((1 - confidence) * baseline_winrate)

            rating = adjusted_winrate * 100

        ratings[player_id] = rating
        logger.info(f"Player {player_id}: {stat['wins']}-{stat['losses']} | Confidence: {min(stat['games'] / confidence_threshold, 1.0):.2f} | Rating: {rating:.1f}")

    return ratings


def balance_teams(players, ratings):
    """
    Balance teams based on player ratings to minimize rating difference.
    """
    if len(players) % 2 != 0:
        raise ValueError("The number of players must be even")

    team_size = len(players) // 2

    # Sort players by rating (highest to lowest)
    sorted_players = sorted(players, key=lambda p: ratings.get(p.id if hasattr(p, 'id') else p, 50), reverse=True)

    # Use a simple alternating draft system
    red_team = []
    blue_team = []

    for i, player in enumerate(sorted_players):
        if i % 2 == 0:
            red_team.append(player)
        else:
            blue_team.append(player)

    # Calculate team ratings
    red_rating = sum(ratings.get(p.id if hasattr(p, 'id') else p, 50) for p in red_team) / len(red_team)
    blue_rating = sum(ratings.get(p.id if hasattr(p, 'id') else p, 50) for p in blue_team) / len(blue_team)

    logger.info(f"Team balance - Red: {red_rating:.1f}, Blue: {blue_rating:.1f}, Diff: {abs(red_rating - blue_rating):.1f}")

    return red_team, blue_team


async def generate_team(players, champions, fixed_teams, choices_number, all_seasons=False):
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
            if len(players) % 2 != 0:
                raise ValueError("The number of players must be even")

        # Use matchmaking to balance teams instead of random shuffle
        try:
            ratings = await calculate_player_ratings(players, all_seasons)
            red_team_players, blue_team_players = balance_teams(players, ratings)
        except Exception as e:
            logger.warning(f"Matchmaking failed, falling back to random: {e}")
            # Fallback to random if matchmaking fails
            random.shuffle(players)
            red_team_players = players[:len(players) // 2]
            blue_team_players = players[len(players) // 2:]

    red_team_champion_names = []
    blue_team_champion_names = []

    for i in range(choices_number if choices_number else team_size * 2):
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
