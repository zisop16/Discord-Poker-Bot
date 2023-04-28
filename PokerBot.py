import discord
from discord.ext import commands
import os
from dotenv import load_dotenv, find_dotenv
import json
import asyncio
import sys, traceback

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
        valid = validate_options(options)
        if not valid:
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

@client.command(name="options", aliases=["setoption", "tableoptions", "option", "tableoption"])
async def options(context, *args):
    if len(args) == 0:
        return
    channel = context.channel
    channelID = channel.id
    if not manager.channel_enabled(channelID):
        return
    userID = context.author.id
    table_name = args[0]
    options = manager.get_table(userID, table_name)
    if not options:
        return
    if len(args) == 1:
        text = f"Options for table: {table_name}```"
        for option in options:
            setting = options[option]
            match(option):
                case "min_buy":
                    setting = f"{setting}bb"
                case "max_buy":
                    setting = f"{setting}bb"
                case "match_stack":
                    setting = "Enabled" if setting else "Disabled"
                case "time_bank":
                    setting = f"{setting} seconds"
                
            text += f"{option}: {setting}\n"
        text += f"\nOptions String:\n{get_options_string(options)}```"
        await channel.send(text)

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
    await channel.send(f"Player: <@{userID}> sitting at seat {seat} with {stack} chips")

@client.command(name="addon", aliases=["add", "rebuy"])
async def addon(context, chips):
    channel = context.channel
    channelID = channel.id
    if channelID not in PokerTable.running:
        return
    userID = context.author.id
    table = PokerTable.running[channelID]
    if not (chips.isnumeric()):
        return
    chips = int(chips)
    success = table.addon(userID, chips)
    if not success:
        await error(channel, f"Failed to increase <@{userID}> stack by {chips} chips")
        return
    seat = table.players.index(userID)
    new_stack = table.game.stacks[seat]
    await channel.send(f"Player: <@{userID}> increased stack to {new_stack} chips")

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

async def message_hand(hand, user):
    await user.send(f"Your Hand:\n{hand_to_string(hand)}")

async def run_clock(channel, current_action_id):
    return
    channelID = channel.id
    table = PokerTable.running[channelID]
    if table.game.street == Streets.End:
        return
    time_bank = table.time_bank
    time_message = await channel.send(f"{time_bank} seconds left to act!")
    update_interval = 3
    while time_bank > 0:
        curr_interval = min(update_interval, time_bank)
        await asyncio.sleep(curr_interval)
        if table.current_action_id != current_action_id:
            return
        time_bank -= curr_interval
        await time_message.edit(content=f"{time_bank} seconds left to act!")
    await continue_action(channel)

async def continue_action(channel):
    channelID = channel.id
    table = PokerTable.running[channelID]
    game = table.game
    table.current_action_id += 1
    acting_seat = game.action_permissions[0]
    playerID = table.players[acting_seat]
    time_bank = table.time_bank
    check = game.may_check()
    if check:
        game.check()
    else:
        acting_seat = game.action_permissions[0]
        game.fold()
        game.sitout(acting_seat)
    await channel.send(f"<@{playerID}> auto-{'checked' if check else 'folded and sat out'} after {time_bank} seconds")
    await channel.send(table.state())
    await run_clock(channel, table.current_action_id)

@client.command(name="deal", aliases=["play"])
async def deal(context):
    channel = context.channel
    channelID = channel.id
    if channelID not in PokerTable.running:
        return
    author = context.author
    userID = author.id
    table = PokerTable.running[channelID]
    game = table.game
    if game.hand_running():
        return
    if userID not in table.players:
        return
    try:
        game.deal()
    except (NoPlayersException, ShortStackException):
        return
    table.current_action_id += 1
    messages = []
    for seat in game.active_seats:
        hand = game.hands[seat]
        playerID = table.players[seat]
        player = client.get_user(playerID)
        messages.append(message_hand(hand, player))
    state = table.state()
    messages.append(channel.send(state))
    await asyncio.gather(*messages)
    await run_clock(channel, table.current_action_id)

def positive_float(num):
    return num.replace(".", "").isnumeric()

def calculate_size(game, size):
    acting_player_seat = game.action_permissions[0]
    acting_player_bet = game.current_bets[acting_player_seat]
    acting_player_stack = game.stacks[acting_player_seat]
    previous_raise = game.previous_raise
    current_bet = game.current_bet
    difference = current_bet - acting_player_bet
    total_pot = game.pot + sum(game.current_bets) + difference
    bb = game.bb
    size = size.lower()
    match(size):
        case "allin" | "ai" | "all" | "stack":
            return acting_player_stack + acting_player_bet
        case "pawt" | "pot":
            return total_pot + current_bet
        case "min" | "minraise" | "minimum":
            return previous_raise + current_bet
    if size.endswith('%'):
        percent = size[:len(size)-1]
        if not positive_float(percent):
            return False
        percent = float(percent) / 100
        return round(total_pot * percent) + current_bet
    if size.endswith("bb"):
        num_bb = size[:len(size)-2]
        if not positive_float(num_bb):
            return False
        return round(float(num_bb) * bb)
    if size.endswith("chips"):
        size = size[:len(size)-5]
    elif size.endswith("c"):
        size = size[:len(size)-1]
    if size.isnumeric():
        return int(size)
    return False
    
@client.command(name="bet", aliases=["raise", "reraise"])
async def bet(context, size):
    channel = context.channel
    channelID = channel.id
    if channelID not in PokerTable.running:
        return
    author = context.author
    userID = author.id
    table = PokerTable.running[channelID]
    game = table.game
    if not game.hand_running():
        return
    if table.acting_player() != userID:
        return
    chips_bet = calculate_size(game, size)
    if not chips_bet:
        return
    try:
        game.bet(chips_bet)
        table.current_action_id += 1
    except InvalidBetException:
        return
        
    await channel.send(table.state())
    await run_clock(channel, table.current_action_id)

@client.command(aliases=["cawl"])
async def call(context):
    channel = context.channel
    channelID = channel.id
    if channelID not in PokerTable.running:
        return
    author = context.author
    userID = author.id
    table = PokerTable.running[channelID]
    game = table.game
    if not game.hand_running():
        return
    if table.acting_player() != userID:
        return
    try:
        game.call()
        table.current_action_id += 1
    except InvalidCallException:
        return

    await channel.send(table.state())
    await run_clock(channel, table.current_action_id)

@client.command()
async def check(context):
    channel = context.channel
    channelID = channel.id
    if channelID not in PokerTable.running:
        return
    author = context.author
    userID = author.id
    table = PokerTable.running[channelID]
    game = table.game
    if not game.hand_running():
        return
    if table.acting_player() != userID:
        return
    try:
        game.check()
        table.current_action_id += 1
    except InvalidCheckException:
        return

    await channel.send(table.state())
    await run_clock(channel, table.current_action_id)

@client.command()
async def fold(context):
    channel = context.channel
    channelID = channel.id
    if channelID not in PokerTable.running:
        return
    author = context.author
    userID = author.id
    table = PokerTable.running[channelID]
    game = table.game
    if not game.hand_running():
        return
    if table.acting_player() != userID:
        return
    game.fold()
    table.current_action_id += 1

    await channel.send(table.state())
    await run_clock(channel, table.current_action_id)

@client.event
async def on_command_error(context, error):
    print(f"Command: {context.command.name} invoked incorrectly")
    raise error

"""
@client.event
async def on_ready():
    while True:
        await asyncio.sleep(1)
        for channelID in PokerTable.running:
            table = PokerTable.running[channelID]
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

