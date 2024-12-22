import copy
import os
import firebase_admin
from aiocache import cached
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter, Or
from google.cloud.firestore_v1.field_path import FieldPath

from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS"))
app = firebase_admin.initialize_app(cred)
db = firestore.client()


# Players Management
async def set_player(name, user):
    """
    Add a new player to the 'players' collection.
    """
    players_ref = db.collection("players")
    players_ref.add({"nome": name, "discord_id": user.id})

    get_players.cache.clear()
    get_player_by_id.cache.clear()
    get_player_by_discord_id.cache.clear()


@cached(ttl=7200)
async def get_players():
    """
    Get all players from the 'players' collection.
    """
    return list(db.collection("players").stream())


@cached(ttl=7200, key_builder=lambda f, *args, **kwargs: f"{f.__name__}:{args[0]}")
async def get_player_by_id(player_id):
    """
    Get a single player document by its ID.
    """
    return db.collection("players").document(player_id).get()


@cached(ttl=7200, key_builder=lambda f, *args, **kwargs: f"{f.__name__}:{args[0]}")
async def get_player_by_discord_id(player_id):
    """
    Get a single player document by its discord ID.
    """
    players_ref = db.collection("players")
    query = players_ref.where(filter=FieldFilter("discord_id", "==", player_id)).limit(1).stream()
    player = next(query, None)
    return player


async def get_players_by_id(ids):
    """
    Get players whose IDs are in the provided list.
    """
    players_ref = db.collection("players")
    result = []
    result.extend(players_ref.where(
        filter=FieldFilter(FieldPath.document_id(), "in", [players_ref.document(_id) for _id in ids])
    ).stream())
    return list(result)


async def get_players_by_discord_id(discord_ids):
    """
    Get players whose Discord IDs are in the provided list.
    """
    return db.collection("players").where(
        filter=FieldFilter("discord_id", "in", discord_ids)
    ).stream()


# Active Players Management
async def add_active_players(players):
    """
    Add players to the active pool.
    """
    players_ref = db.collection("matches_settings").document("pool")
    firebase_players = [p.id for p in await get_players_by_discord_id(players)]

    if players_ref.get().exists:
        players_ref.update({"list": firestore.ArrayUnion(firebase_players)})
    else:
        players_ref.set({"list": firebase_players})

    await get_active_players.cache.clear()


async def remove_active_player(player_id):
    """
    Remove a player from the active pool.
    """
    players_ref = db.collection("matches_settings").document("pool")
    players_ref.update({"list": firestore.ArrayRemove([player_id])})

    await get_active_players.cache.clear()


async def clear_active_players():
    """
    Clear the active players list and reset configurations.
    """
    db.collection("matches_settings").document("pool").set({"list": []})
    db.collection("matches_settings").document("teams").set({"A": [], "B": []})

    await set_config("fixed_teams", False)

    await get_active_players.cache.clear()


@cached(ttl=7200)
async def get_active_players():
    """
    Retrieve the list of active players or fixed teams if enabled.
    """
    config = db.collection("matches_settings").document("config").get()
    if config.get("fixed_teams"):
        player_list = db.collection("matches_settings").document("teams").get()

        teams_discord = {
            "A": await get_players_by_id(player_list.get("A")),
            "B": await get_players_by_id(player_list.get("B"))
        }
        return teams_discord
    else:
        player_list = db.collection("matches_settings").document("pool").get().get("list")
        return list(await get_players_by_id(player_list) if player_list else [])


# Fixed Teams Management
async def add_fixed_players(players, team):
    """
    Add players to a fixed team.
    """
    players_ref = db.collection("matches_settings").document("teams")
    firebase_players = [p.id for p in await get_players_by_discord_id([player.id for player in players])]
    players_ref.update({team: firebase_players})

    await get_active_players.cache.clear()


# Match Management
async def store_match(match):
    """
    Store a match in the database.
    """
    match = copy.deepcopy(match)
    match["timestamp"] = firestore.SERVER_TIMESTAMP
    match["result"] = "UNFINISHED"
    match["mode"] = len(match["red_team"]["players"])
    match["blue_team"]["players"] = [player.id for player in match["blue_team"]["players"]]
    match["red_team"]["players"] = [player.id for player in match["red_team"]["players"]]
    result = db.collection("matches").add(match)

    await get_finished_matches.cache.clear()
    await get_matches_by_player.cache.clear()
    return result[1].id


async def set_match_victory(match_id, result):
    """
    Set the result of a match.
    """
    db.collection("matches").document(match_id).update({"result": result})

    await get_finished_matches.cache.clear()
    await get_matches_by_player.cache.clear()


@cached(ttl=7200, key_builder=lambda f, *args, **kwargs: f"{f.__name__}:{args[0]}:{args[1]}")
async def get_finished_matches(mode, season):
    """
    Retrieve all finished matches with optional filtering by mode.
    """
    query = (
        db
        .collection("matches")
        .where(filter=FieldFilter("result", "!=", 'UNFINISHED'))
        .where(filter=FieldFilter("timestamp", ">=", season.get("start")))
        .where(filter=FieldFilter("timestamp", "<=", season.get("end")))
    )
    if mode:
        query = query.where(filter=FieldFilter("mode", "==", mode))
    return list(query.stream())


@cached(ttl=7200, key_builder=lambda f, *args, **kwargs: f"{f.__name__}:{args[0]}:{args[1]}")
async def get_matches_by_player(player_id, limit):
    """
    Retrieve the last N matches of the specified player.
    """
    query = (
        db.collection("matches")
        .where(filter=FieldFilter("result", "!=", "UNFINISHED"))
        .where(
            filter=Or(
                [
                    FieldFilter("blue_team.players", "array_contains", player_id),
                    FieldFilter("red_team.players", "array_contains", player_id),
                ]
            )
        )
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )

    return list(query.stream())


# Configuration Management
async def set_config(config, value):
    """
    Set a configuration in the database.
    """
    db.collection("matches_settings").document("config").set({config: value})

    await get_config.cache.clear()


@cached(ttl=7200, key_builder=lambda f, *args, **kwargs: f"{f.__name__}:{args[0]}")
async def get_config(config):
    """
    Get a specific configuration value.
    """
    return db.collection("matches_settings").document("config").get().get(config)


# Season Management
@cached(ttl=7200)
async def get_last_season():
    """
    Get last season.
    """
    query = (
        db.collection("seasons")
        .order_by("id", direction=firestore.Query.DESCENDING)
        .limit(1)
    )

    return list(query.stream())[0]


@cached(ttl=7200, key_builder=lambda f, *args, **kwargs: f"{f.__name__}:{args[0]}")
async def get_season_by_id(season_id: int):
    """
    Get season by the specified id.
    """
    query = (
        db.collection("seasons")
        .where(filter=FieldFilter("id", "==", season_id))
        .limit(1)
    )

    result = list(query.stream())

    return result[0] if result else None


async def create_new_season():
    """
    Create a new season.
    """
    last_season = await get_last_season()
    new_season = {
        "id": last_season.get("id") + 1,
        "start": firestore.SERVER_TIMESTAMP,
        "end": last_season.get("end")
    }

    db.collection("seasons").document(last_season.id).update({"end": firestore.SERVER_TIMESTAMP})
    result = db.collection("seasons").add(new_season)

    await get_last_season.cache.clear()
    await get_season_by_id.cache.clear()

    return result[1].get()

