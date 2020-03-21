import os

# External packages
import discord
from dotenv import load_dotenv
import yaml

# Specific to this bot
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

    handler_funcs = {
        '!test': handle_test_request,

        '!createlobby': handle_create_lobby_request,
        '!openlobby': handle_create_lobby_request,
        '!open': handle_create_lobby_request,

        '!joinlobby': handle_join_lobby_request,
        '!join': handle_join_lobby_request,

        '!leavelobby': handle_leave_lobby_request,
        '!leave': handle_leave_lobby_request,

        '!closelobby': handle_close_lobby_request,
        '!close': handle_close_lobby_request,

        '!status': print_lobby_status,
        '!+': print_lobby_status,

        '!help': handle_help_request
    }

    if handler_funcs.get(message.content):
        await handler_funcs[message.content](message)


# !help
async def handle_help_request(message):
    response = '\n\n'.join([
        'I am a Discord bot whose purpose is to maintain a Discord lobby for people who want to play WC3 Football but also want to continue going about their business until there are enough people to play a full game.',

        'Available commands are:',

        '**!open**: If no lobby is currently open, will start a lobby where players can sign up to be notified once enough players are ready to go.',

        '**!join**: Joins the lobby. You will be pinged in Discord once the lobby has reached the configured number of players (default is 8), and the expectation is that you will be available to join the WC3 lobby within a reasonable amount of time.',

        '**!leave**: Leaves the lobby. Your name will not show up in the list of players ready to go, and you will not be pinged.',

        '**!close**: Closes the lobby. Only executable by the owner of the current lobby.',

        '**!status**: Outputs the current lobby situation.'
    ])

    # Send the user a DM with the above response
    user = message.author
    await user.create_dm()
    await user.dm_channel.send(response)

    # React to their message with a thumbs up
    emoji = '\N{THUMBS UP SIGN}'
    await message.add_reaction(emoji)


# !test
async def handle_test_request(message):
    await message.channel.send('Yes hello I am here')


# !createlobby, !openlobby, !open
async def handle_create_lobby_request(message):
    global lobby

    # Check for existing lobby
    if lobby is not None:
        # Check if owner tried to open another lobby
        if lobby.is_owner(message.author):
            await message.channel.send('You already have an open lobby.')
            return

        # Notify that a lobby is already open
        await message.channel.send(f'{lobby.get_owner()} has a lobby open. Type !join to ready up.')
        return

    # Create the lobby
    lobby = Lobby(message.author)

    # Notify
    await message.channel.send(f'{message.author} is starting a lobby. Type !join to ready up.')


# !joinlobby, !join
async def handle_join_lobby_request(message):
    global lobby

    # Check for if no lobby is currently open
    if lobby is None:
        await message.channel.send(f'There is no lobby currently open. Type !openlobby to start one.')
        return

    # Check if the user is already in the lobby
    if lobby.contains_user(message.author):
        return

    # Add the user to the lobby
    lobby.add_user(message.author)

    # Notify that the join request is successful
    await message.channel.send(f'{message.author} is ready to play.')

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
    await message.channel.send(f'{message.author} left the lobby.')
    await check_lobby_status(message)


# !closelobby, !close
async def handle_close_lobby_request(message):
    global lobby

    # Only the owner of the lobby can close it
    if lobby.is_owner(message.author):
        await message.channel.send(f'{message.author} has closed the lobby.')
        lobby = None


# !status, !+
async def print_lobby_status(message):
    global lobby

    # Check for open lobby
    if lobby is None:
        print(f'Could not print lobby status as no lobby was open.')
        await message.channel.send(f'There is no lobby currently open. Type !open to start one.')
        return

    # Get player counts
    user_count = lobby.user_count()
    users_still_required = config['players_to_begin'] - user_count

    # To be grammatically correct
    separator = 'is' if user_count == 1 else 'are'

    # Send message containing all users currently readied up
    await message.channel.send(f'{str(lobby)} {separator} ready to play. {users_still_required} more are required to begin.')


# -----
# Helper functions
# -----

# Determines if the lobby currently has enough players to begin.
def is_lobby_at_critical_mass():
    global lobby

    return lobby.user_count() >= config['players_to_begin']


# Checks the number of users in the lobby and actions appropriately for an empty or full lobby.
async def check_lobby_status(message):
    global lobby

    user_count = lobby.user_count()
    if user_count is 0:
        await message.channel.send(f'{message.author} was the only user readied up. Closing the lobby.')
        return
    elif is_lobby_at_critical_mass():
        await notify_start_game(message)


# Notifies everyone that the lobby is ready to go
async def notify_start_game(message):
    await message.channel.send(f'Enough players have readied up for a game to begin! One person needs to start a WC3 lobby and post the game name here. This discord lobby has been closed.')
    await ping_readied_players(message)


# Sends a message pinging all players in the lobby
async def ping_readied_players(message):
    global lobby

    players = lobby.get_users()

    # discord.User.mention is the attribute we need to ping a Discord User
    # https://discordpy.readthedocs.io/en/latest/api.html#discord.User.mention
    await message.channel.send(' '.join([user.mention for user in players]))


client.run(TOKEN)