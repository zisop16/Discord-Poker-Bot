import discord
import os
from dotenv import load_dotenv, find_dotenv
import json

from DataManager import *
from CommandInterface import *

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    # dog man's server, #general
    """
    working_guild = client.guilds[0]
    working_channel = working_guild.text_channels[0]
    """

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    valid = interface.parse_command(message)
    print(valid)

load_dotenv(find_dotenv())
token = os.getenv("TOKEN")
password = os.getenv("MONGO_PASS")
manager = DataManager(password)
interface = CommandInterface(manager)

client.run(token)

