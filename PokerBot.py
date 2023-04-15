import discord
import os
from dotenv import load_dotenv, find_dotenv
import json
from DataManager import *
from PokerGame import *

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

with open("emojis.json") as emoji_file:
    emojis = json.loads(emoji_file)["Chess"]


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    # dog man's server, #general
    working_guild = client.guilds[0]
    working_channel = working_guild.text_channels[0]


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    print(f"Message: /{message.content}/")
    # await message.channel.send("Hi")
    if message.content.startswith('chess '):
        await message.channel.send("Hello")

load_dotenv(find_dotenv())
token = os.getenv("TOKEN")
client.run(token)
