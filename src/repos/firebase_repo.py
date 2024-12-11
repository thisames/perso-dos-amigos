import copy
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.field_path import FieldPath

from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS"))
app = firebase_admin.initialize_app(cred)
db = firestore.client()


# Players Management
def set_player(name, user):
    """
    Add a new player to the 'players' collection.
    """
    players_ref = db.collection("players")
    players_ref.add({"nome": name, "discord_id": user.id})


def get_players():
    """
    Get all players from the 'players' collection.
    """
    return db.collection("players").stream()


def get_player_by_id(player_id):
    """
    Get a single player document by its ID.
    """
    return db.collection("players").document(player_id).get()


def get_players_by_id(ids):
    """
    Get players whose IDs are in the provided list.
    """
    players_ref = db.collection("players")
    result = []
    result.extend(players_ref.where(
        filter=FieldFilter(FieldPath.document_id(), "in", [players_ref.document(_id) for _id in ids])
    ).stream())
    return result


def get_players_by_discord_id(discord_ids):
    """
    Get players whose Discord IDs are in the provided list.
    """
    return db.collection("players").where(
        filter=FieldFilter("discord_id", "in", discord_ids)
    ).stream()


# Active Players Management
def add_active_players(players):
    """
    Add players to the active pool.
    """
    players_ref = db.collection("matches_settings").document("pool")
    firebase_players = [p.id for p in get_players_by_discord_id([player.id for player in players])]

    if players_ref.get().exists:
        players_ref.update({"list": firestore.ArrayUnion(firebase_players)})
    else:
        players_ref.set({"list": firebase_players})


def remove_active_player(player_id):
    """
    Remove a player from the active pool.
    """
    players_ref = db.collection("matches_settings").document("pool")
    players_ref.update({"list": firestore.ArrayRemove([player_id])})


def clear_active_players():
    """
    Clear the active players list and reset configurations.
    """
    db.collection("matches_settings").document("pool").set({"list": []})
    db.collection("matches_settings").document("config").set({"fixed_teams": False})
    db.collection("matches_settings").document("teams").set({"A": [], "B": []})


def get_active_players():
    """
    Retrieve the list of active players or fixed teams if enabled.
    """
    config = db.collection("matches_settings").document("config").get()
    if config.get("fixed_teams"):
        player_list = db.collection("matches_settings").document("teams").get()

        teams_discord = {
            "A": get_players_by_id(player_list.get("A")),
            "B": get_players_by_id(player_list.get("B"))
        }
        return teams_discord
    else:
        player_list = db.collection("matches_settings").document("pool").get().get("list")
        return get_players_by_id(player_list)


# Fixed Teams Management
def add_fixed_players(players, team):
    """
    Add players to a fixed team.
    """
    players_ref = db.collection("matches_settings").document("teams")
    firebase_players = [p.id for p in get_players_by_discord_id([player.id for player in players])]
    players_ref.update({team: firebase_players})


def set_fixed_team(players, team_name):
    """
    Set the roster of a fixed team.
    """
    db.collection("matches_settings").document("teams").set({team_name: players})


# Match Management
def store_match(match):
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
    return result[1].id


def set_match_victory(match_id, result):
    """
    Set the result of a match.
    """
    db.collection("matches").document(match_id).update({"result": result})


def get_finished_matches(mode):
    """
    Retrieve all finished matches with optional filtering by mode.
    """
    query = db.collection("matches").where(filter=FieldFilter("result", "!=", 'UNFINISHED'))
    if mode:
        query = query.where(filter=FieldFilter("mode", "==", mode))
    return query.stream()


# Configuration Management
def set_config(config, value):
    """
    Set a configuration in the database.
    """
    db.collection("matches_settings").document("config").set({config: value})


def get_config(config):
    """
    Get a specific configuration value.
    """
    return db.collection("matches_settings").document("config").get().get(config)
