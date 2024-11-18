import os
import discord
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from dotenv import load_dotenv

load_dotenv()

cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS'))
app = firebase_admin.initialize_app(cred)

db = firestore.client()


def set_player(name, user):
    players_ref = db.collection("players")
    players_ref.add({"nome": name, "discordId": user.id})


def get_players():
    players_ref = db.collection("players")
    players = players_ref.stream()

    result = []
    for player in players:
        result.append(discord.SelectOption(label=player.get('nome'), value=str(player.id)))

    return result


def get_players_max_size():
    players_ref = db.collection("players")
    result = players_ref.count().get()
    return min(result[0][0].value, 10)


def add_active_players(players):
    players_ref = db.collection("active_players").document('players')
    players_ref.set({"list": firestore.ArrayUnion(players)})


def clear_active_players():
    players_ref = db.collection("active_players").document('players')
    players_ref.set({"list": []})


def get_active_players():
    players = db.collection("active_players").document("players").get()
    print(players)
    print(players.to_dict())
    return players.get("list")
