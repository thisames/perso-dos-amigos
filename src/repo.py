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


def get_players_max_size():
    players_ref = db.collection("players")
    result = players_ref.count().get()
    return min(result[0][0].value, 10)


def add_active_players(players):
    players_ref = db.collection("active_players").document("players")

    if players_ref.get().exists:
        players_ref.update({"list": firestore.ArrayUnion(players)})
    else:
        players_ref.set({"list": players})


def remove_active_player(player):
    players_ref = db.collection("active_players").document("players")
    players_ref.update({"list": firestore.ArrayRemove([player])})


def clear_active_players():
    players_ref = db.collection("active_players").document("players")
    players_ref.set({"list": []})


def get_active_players():
    players = db.collection("active_players").document("players").get()
    return players.get("list")


def store_match(match):
    matches_ref = db.collection("matches")
    match["timestamp"] = firestore.SERVER_TIMESTAMP
    match["result"] = "UNFINISHED"
    result = matches_ref.add(match)
    return result[1].id


def set_match_victory(match_id, result):
    matches_ref = db.collection("matches").document(match_id)
    matches_ref.update({"result": result})


def get_finished_matches():
    matches = (
        db.collection("matches")
        .where(filter=FieldFilter("result", "!=", 'UNFINISHED'))
        .stream()
    )
    return matches
