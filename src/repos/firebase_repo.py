import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from dotenv import load_dotenv

load_dotenv()

cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS"))
app = firebase_admin.initialize_app(cred)

db = firestore.client()


def set_player(name, user):
    players_ref = db.collection("players")
    players_ref.add({"nome": name, "discord_id": user.id})


def get_players():
    players_ref = db.collection("players")
    return players_ref.stream()


def get_player_by_id(player):
    player = db.collection("players").document(player).get()
    return player


def get_players_by_discord_id(players):
    players = (
        db.collection("players").where(filter=FieldFilter("discord_id", "in", players)).stream()
    )
    return players


def add_active_players(players):
    players_ref = db.collection("matches_settings").document("pool")

    firebase_players = [f_player.id for f_player in get_players_by_discord_id([player.id for player in players])]

    if players_ref.get().exists:
        players_ref.update({"list": firestore.ArrayUnion(firebase_players)})
    else:
        players_ref.set({"list": firebase_players})


def add_fixed_players(players, team):
    players_ref = db.collection("matches_settings").document("teams")

    firebase_players = [f_player.id for f_player in get_players_by_discord_id([player.id for player in players])]

    players_ref.update({team: firebase_players})


def set_fixed_team(players, name):
    players_ref = db.collection("matches_settings").document("teams")

    players_ref.set({name: players})


def remove_active_player(player):
    players_ref = db.collection("matches_settings").document("pool")
    players_ref.update({"list": firestore.ArrayRemove([player])})


def clear_active_players():
    players_ref = db.collection("matches_settings").document("pool")
    players_ref.set({"list": []})

    config_ref = db.collection("matches_settings").document("config")
    config_ref.set({"fixed_teams": False})

    team_ref = db.collection("matches_settings").document("teams")
    team_ref.set({"A": [], "B": []})


def get_active_players():
    config = db.collection("matches_settings").document("config").get()

    if config.get("fixed_teams"):
        return db.collection("matches_settings").document("teams").get()
    else:
        players = db.collection("matches_settings").document("pool").get()
        return players.get("list")


def store_match(match):
    matches_ref = db.collection("matches")
    match["timestamp"] = firestore.SERVER_TIMESTAMP
    match["result"] = "UNFINISHED"
    match["mode"] = len(match["red_team"]["players"])
    result = matches_ref.add(match)
    return result[1].id


def set_match_victory(match_id, result):
    matches_ref = db.collection("matches").document(match_id)
    matches_ref.update({"result": result})


def get_finished_matches(mode):
    query = db.collection("matches").where(filter=FieldFilter("result", "!=", 'UNFINISHED'))

    if mode:
        query = query.where(filter=FieldFilter("mode", "==" if mode else "!=", mode))

    matches = (
        query.stream()
    )
    return matches


def set_config(config, value):
    config_ref = db.collection("matches_settings").document("config")
    config_ref.set({config: value})


def get_config(config):
    config_ref = db.collection("matches_settings").document("config")
    return config_ref.get().get(config)
