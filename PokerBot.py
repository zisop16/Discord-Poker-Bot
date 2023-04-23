import discord
from discord.ext import commands
import os
from dotenv import load_dotenv, find_dotenv
import json

from DataManager import *
from PokerTable import *

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

async def error(channel, message):
    await channel.send(f"Error: {message}")

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
        await error(channel, "Please enter a positive integer amount")
        return
    giverID = context.author.id
    giver_balance = manager.get_chips(giverID)
    amount = min(giver_balance, amount)
    manager.add_chips(mentioned, amount)
    manager.remove_chips(giverID, amount)
    await channel.send(f"<@{giverID}> gave {amount} chips to <@{mentioned}>")

@client.command(name="create")
async def create_table(context, *args):
    channel = context.channel
    enabled = manager.channel_enabled(channel.id)
    if not enabled:
        return
    if len(args) == 1:
        options = default_table_options()
    elif len(args) == 2:
        options = eval_options_string(args[1])
        if not options:
            await error(channel, "Invalid options string")
    else:
        return
    name = args[0]
    userID = context.author.id
    if manager.table_exists(userID, name):
        await error(channel, "You've already created a table with that name")
        return
    success = manager.create_table(userID, name, options)
    if success:
        await channel.send(f"<@{userID}> created table {name}")
    else:
        await error(channel, "You've already created the maximum number of tables")

@client.command(name="delete")
async def delete_table(context, table_name):
    channel = context.channel
    enabled = manager.channel_enabled(channel.id)
    if not enabled:
        return
    userID = context.author.id
    if not manager.table_exists(userID, table_name):
        return
    manager.delete_table(userID, table_name)
    await channel.send(f"<@{userID}> deleted table {table_name}")
    
@client.command(name="open", aliases=["opentable", "starttable", "runtable", "run"])
async def open_table(context, table_name):
    channel = context.channel
    enabled = manager.channel_enabled(channel.id)
    if not enabled:
        return
    userID = context.author.id
    channelID = context.channel.id
    if channelID in PokerTable.running:
        await error(channel, f"Table {PokerTable.running[channelID].name} is already running in this channel")
        return
    options = manager.get_table(userID, table_name)
    if not options:
        await error(channel, f"You do not own a table named {table_name}")
        return
    table = PokerTable(table_name, channelID, userID, options, manager)
    await channel.send(f"Table {table_name} is now running")

@client.command(name="close", aliases=["closetable", "endtable", "end"])
async def close_table(context):
    channel = context.channel
    if channel.id not in PokerTable.running:
        return
    table = PokerTable.running[channel.id]
    authorID = context.author.id
    channel_manager = context.author.guild_permissions.manage_channels
    may_close = channel_manager or authorID == table.runnerID
    if not may_close:
        return
    close(channel.id)
    await channel.send(f"Closed table: {table.name}")

@client.command(name="buyin", aliases=["buy"])
async def buyin(context, seat, stack):
    channel = context.channel
    channelID = channel.id
    if channelID not in PokerTable.running:
        return
    userID = context.author.id
    table = PokerTable.running[channelID]
    if not (seat.isnumeric() and stack.isnumeric()):
        return
    seat = int(seat)
    stack = int(stack)
    success = table.buyin(userID, seat, stack)
    if not success:
        await error(channel, f"Failed to buyin at seat {seat} with {stack} chips")
        return
    await channel.send(f"Player: <@{userID}> sitting at seat: {seat} with {stack} chips")

@client.command(name="sitin", aliases=["sit", "sitdown"])
async def sitin(context):
    channel = context.channel
    channelID = channel.id
    if channelID not in PokerTable.running:
        return
    userID = context.author.id
    table = PokerTable.running[channelID]
    success = table.sitin(userID)
    if not success:
        return
    await channel.send(f"Player: <@{userID}> sitting in")

@client.command(name="sitout", aliases=["situp", "stand"])
async def sitout(context):
    channel = context.channel
    channelID = channel.id
    if channelID not in PokerTable.running:
        return
    userID = context.author.id
    table = PokerTable.running[channelID]
    success = table.sitout(userID)
    if not success:
        return
    await channel.send(f"Player <@{userID}> has stood up")

@client.command(name="cashout", aliases=["cash", "leave", "buyout"])
async def cashout(context):
    channel = context.channel
    channelID = channel.id
    if channelID not in PokerTable.running:
        return
    userID = context.author.id
    table = PokerTable.running[channelID]
    success = table.cashout(userID)
    if not success:
        return
    chips = 0 if success == -1 else success
    await channel.send(f"Player <@{userID}> cashed out for {chips} chips")

@client.command(name="deal", aliases=["play"])
async def deal(context):
    pass
    
@client.command(name="bet", aliases=["raise", "reraise"])
async def bet(context, size):
    pass

@client.command()
async def call(context):
    pass

@client.command()
async def check(context):
    pass

@client.command()
async def fold(context):
    pass

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

