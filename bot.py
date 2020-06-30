# Discord Lobby Bot
# Author: Marc Suesser
# 
#
#

# Standard library imports
import os

# Third party imports
import discord
from dotenv import load_dotenv
import yaml
import random

# Local application imports
from src.lobby import Lobby

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Load configuration values from config.yaml
config = None
with open("src/config.yaml", 'r') as ymlfile:
    # Loader=yaml.SafeLoader comes from a warning PyYAML issues if not specified
    # See https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation for more
    config = yaml.load(ymlfile, Loader=yaml.SafeLoader)

print(config)

PLAYERS_TO_BEGIN = config['players_to_begin']
ADMIN_USERS = config['admin_users']
AUTH_USERS = config['auth_users']
SELF_DESTRUCT_TIME = config['self_destruct_time']

client = discord.Client()

# Currently open lobby
lobby = None

# Bot is alive
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

# Event hook to process all messages sent to the server
@client.event
async def on_message(message):
    # Do not process any messages sent by this bot
    if message.author == client.user:
        return

    # Allow messages from myself for testing purposes
    global ADMIN_USERS
    if isinstance(message.channel, discord.DMChannel) and message.recipient.name in ADMIN_USERS:
        return

    # Only process channel messages from #general
    if isinstance(message.channel, discord.TextChannel) and message.channel.name != 'general':
        return

    handler_funcs = {
        '!test': handle_test_request,
        '!coinflip': handle_coinflip_request,

        '!createlobby': handle_create_lobby_request,
        '!openlobby': handle_create_lobby_request,
        '!open': handle_create_lobby_request,
        '!o': handle_create_lobby_request,

        '!joinlobby': handle_join_lobby_request,
        '!join': handle_join_lobby_request,
        '!ready': handle_join_lobby_request,
        '!j': handle_join_lobby_request,

        '!leavelobby': handle_leave_lobby_request,
        '!leave': handle_leave_lobby_request,
        '!out': handle_leave_lobby_request,
        '!gottago': handle_leave_lobby_request,
        '!l': handle_leave_lobby_request,

        '!closelobby': handle_close_lobby_request,
        '!close': handle_close_lobby_request,
        '!c': handle_close_lobby_request,

        '!status': print_lobby_status,
        '!lobby': print_lobby_status,
        '!+': print_lobby_status,

        '!help': handle_help_request,
        '!?': handle_help_request
    }

    if handler_funcs.get(message.content):
        await handler_funcs[message.content](message)


# !help
async def handle_help_request(message):
    global PLAYERS_TO_BEGIN
    response = '\n\n'.join([
        f'Football Lobby Guy\'s purpose is to maintain a Discord lobby for people who want to play WC3 Football but also want to continue going about their business until there are enough people to play a full game. It\'s simple: if you want to play football, create or join a lobby, and once there are {PLAYERS_TO_BEGIN} players ready to go I will ping those 8 players to let them know it\'s time.',

        'Commands:',

        '__**!open**__: If no lobby is currently open, will start a lobby where players can sign up to be notified once enough players are ready to go. Aliases: **!openlobby, !createlobby, !o**',

        '__**!join**__: Joins the lobby. You will be pinged in Discord once the lobby has reached the configured number of players (default is 8), and the expectation is that you will be available to join the WC3 lobby within a reasonable amount of time. Aliases: **!joinlobby, !ready, !j**',

        '__**!leave**__: Leaves the lobby. Your name will not show up in the list of players ready to go, and you will not be pinged. Aliases: **!leavelobby, !out, !gottago, !l**',

        '__**!close**__: Closes the lobby. Only executable by the owner of the current lobby. Aliases: **!closelobby, !c**',

        '__**!status**__: Outputs the current lobby situation. Aliases: **!lobby, !+**',

        '__**!help**__: Receive this message. Aliases: **!?**'
    ])

    # Send the user a DM with the above response
    user = message.author
    await user.create_dm()
    await user.dm_channel.send(response)

    await thumbs_up_msg(message)


# !test
async def handle_test_request(message):
    global SELF_DESTRUCT_TIME
    await message.channel.send('Yes hello I am here', delete_after=SELF_DESTRUCT_TIME)

async def handle_coinflip_request(message):
    result = random.choice(('Heads', 'Tails'))
    await message.channel.send(result)


# !createlobby, !openlobby, !open
async def handle_create_lobby_request(message):
    global lobby
    global SELF_DESTRUCT_TIME

    # Check for existing lobby
    if lobby is not None:
        # Check if owner tried to open another lobby
        if lobby.is_owner(message.author):
            await message.channel.send('You already have an open lobby.', delete_after=SELF_DESTRUCT_TIME)
            return

        # Notify that a lobby is already open
        await message.channel.send(f'{lobby.get_owner()} has a lobby open. Type !join to ready up.', delete_after=SELF_DESTRUCT_TIME)
        return

    # Create the lobby
    lobby = Lobby(message.author)

    # Notify
    await thumbs_up_msg(message)
    await message.channel.send(f'{message.author} is starting a lobby. Type !join to ready up.')


# !joinlobby, !join
async def handle_join_lobby_request(message):
    global lobby
    global SELF_DESTRUCT_TIME

    # Check for if no lobby is currently open
    if lobby is None:
        await message.channel.send(f'There is no lobby open. Type !open to start one.', delete_after=SELF_DESTRUCT_TIME)
        return

    # Check if the user is already in the lobby
    if lobby.contains_user(message.author):
        return

    # Add the user to the lobby
    lobby.add_user(message.author)

    # Notify that the join request is successful by reacting with thumbs up
    await thumbs_up_msg(message)

    # Check to see if number of users has reached critical mass
    await check_lobby_status(message)


# !leavelobby, !leave
async def handle_leave_lobby_request(message):
    global lobby

    # Check for if no lobby is currently open
    if lobby is None:
        return

    # Confirm that the user is actually in the lobby to begin with
    if not lobby.contains_user(message.author):
        return
    
    # Remove the user, notify the channel, and check the lobby to see if the lobby is now empty
    lobby.remove_user(message.author)
    await thumbs_up_msg(message)
    await check_lobby_status(message)


# !closelobby, !close
async def handle_close_lobby_request(message):
    global lobby
    global AUTH_USERS

    # Only the owner of the lobby can close it, or authenticated users
    if lobby.is_owner(message.author) or message.author.name in AUTH_USERS:
        await thumbs_up_msg(message)
        lobby = None


# !status, !+
async def print_lobby_status(message):
    global lobby
    global PLAYERS_TO_BEGIN

    # Check for open lobby
    if lobby is None:
        print(f'Could not print lobby status as no lobby was open.')
        await message.channel.send(f'There is no lobby open. Type !open to start one.')
        return

    # Get player counts
    user_count = lobby.user_count()
    users_still_required = PLAYERS_TO_BEGIN - user_count

    # To be grammatically correct
    separator = 'is' if user_count == 1 else 'are'

    # Send message containing all users currently readied up
    await message.channel.send(f'{str(lobby)} {separator} ready to go. Need {users_still_required} more.')


# -----
# Helper functions
# -----

# Determines if the lobby currently has enough players to begin.
def is_lobby_at_critical_mass():
    global lobby
    global PLAYERS_TO_BEGIN

    return lobby.user_count() >= PLAYERS_TO_BEGIN


# Checks the number of users in the lobby and actions appropriately for an empty or full lobby.
async def check_lobby_status(message):
    global lobby
    global SELF_DESTRUCT_TIME

    user_count = lobby.user_count()
    if user_count is 0:
        await message.channel.send(f'The lobby is now empty. Closing.', delete_after=SELF_DESTRUCT_TIME)
        lobby = None
        return
    elif is_lobby_at_critical_mass():
        await notify_start_game(message)


# Notifies everyone that the lobby is ready to go
async def notify_start_game(message):
    global PLAYERS_TO_BEGIN
    await message.channel.send(f'{PLAYERS_TO_BEGIN} players are ready to go! One person needs to start a WC3 lobby and post the game name here. Closing this Discord lobby.')
    await ping_readied_players(message)
    await handle_close_lobby_request(message)


# Sends a message pinging all players in the lobby
async def ping_readied_players(message):
    global lobby

    players = lobby.get_users()

    # discord.User.mention is the attribute we need to ping a Discord User
    # https://discordpy.readthedocs.io/en/latest/api.html#discord.User.mention
    await message.channel.send(' '.join([user.mention for user in players]))


# React to their message with a thumbs up
async def thumbs_up_msg(message):
    emoji = '\N{THUMBS UP SIGN}'
    await message.add_reaction(emoji)


client.run(TOKEN)