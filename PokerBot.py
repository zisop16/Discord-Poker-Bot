import discord
from discord.ext import commands
import os
from dotenv import load_dotenv, find_dotenv
import json

from DataManager import *
from CommandInterface import *

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = commands.Bot(command_prefix='-', help_command=None, intents=intents, case_insensitive=True)
load_dotenv(find_dotenv())
token = os.getenv("TOKEN")
password = os.getenv("MONGO_PASS")
manager = DataManager(password)
# interface = CommandInterface(manager)

def get_mentioned(mention_text):
    if len(mention_text) > 3:
        if mention_text.startswith("<@") and mention_text.endswith(">"):
            middle = mention_text[2:len(mention_text)-1]
            if middle.isnumeric():
                return int(middle)
    return False

@client.command(name="enable")
@commands.has_permissions(manage_channels=True)
async def enable_channel(context):
    id = context.channel.id
    manager.enable_channel(id)

@client.command(name="disable")
@commands.has_permissions(manage_channels=True)
async def disable_channel(context):
    id = context.channel.id
    manager.disable_channel(id)

@client.command(name="chips", aliases=["getchips", "beg", "freechips"])
async def free_chips(context):
    channelID = context.channel.id
    channel_enabled = manager.channel_enabled(channelID)
    if channel_enabled:
        userID = context.author.id
        received, remaining_time = manager.generate_chips(userID)
        if received:
            await context.channel.send(f"Granted <@{userID}> {DataManager.free_chips} chips")
        else:
            await context.channel.send(f"Please wait {int(remaining_time)} seconds before asking for chips again")

@client.command(name="balance", aliases=["money", "getbalance", "bal"])
async def get_balance(context, *args):
    channel = context.channel
    channelID = channel.id
    channel_enabled = manager.channel_enabled(channelID)
    if not channel_enabled:
        return
    specific_user = False
    if len(args) > 0:
        specific_user = True
        arg1 = args[0]
    if specific_user:
        mentioned = get_mentioned(arg1)
        if not mentioned:
            return
        guild = context.guild
        if guild.get_member(mentioned) is None:
            return
        userID = mentioned
    else:
        userID = context.author.id
    balance = manager.get_chips(userID)
    await channel.send(f"<@{userID}> has {balance} chips")

@client.command(name="give", aliases=["transfer", "donate"])
async def give(context, user, amount):
    channel = context.channel
    channel_enabled = manager.channel_enabled(channel.id)
    if not channel_enabled:
        return
    mentioned = get_mentioned(user)
    if not mentioned:
        return
    guild = context.guild
    if guild.get_member(mentioned) is None:
        return
    if amount.isnumeric():
        amount = int(amount)
    else:
        return
    giver_id = context.author.id
    giver_balance = manager.get_chips(giver_id)
    amount = min(giver_balance, amount)
    manager.add_chips(mentioned, amount)
    manager.remove_chips(giver_id, amount)
    await channel.send(f"<@{giver_id}> gave {amount} chips to <@{mentioned}>")

@client.event
async def on_command_error(context, error):
    print(f"Command: {context.command.name} invoked incorrectly")
    print(error)

"""
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    # dog man's server, #general
    working_guild = client.guilds[0]
    working_channel = working_guild.text_channels[0]
"""


"""
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    valid = interface.parse_command(message)
    print(valid)
"""



client.run(token)

