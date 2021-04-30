import argparse
import random
import traceback
import discord
import os

TOKEN = os.environ["TOKEN"]
COMMANDS = {}


def command(expected_args, help):
    def decorator(func):
        COMMANDS[func.__name__] = (expected_args, func, help)
        return func
    return decorator


@command([("name", str)], help="greets a human")
async def hello(channel, author, args):
    await channel.send("hello " + args["name"] + "!")


@command([], help="displays this help text")
async def help(channel, author, args):
    await channel.send(get_help())


@command([("number_of_teams", int)], help="group voice channel members into teams")
async def teams(channel, author, args):
    if author.voice is None:
        await channel.send(author.mention + ", you're not in a voice channel!")
        return
    no_teams = args["number_of_teams"]
    if no_teams < 2:
        await channel.send(author.mention + ", the number of teams must be >= 2!")
        return
    guild = channel.guild

    first_channel = author.voice.channel.position
    if first_channel + no_teams - 1 >= len(guild.voice_channels):
        await channel.send(author.mention + ", not enough voice channels below the current one")
        return
    voice_channels = guild.voice_channels[ first_channel : first_channel + no_teams ]
    members = [guild.get_member(i) for i in author.voice.channel.voice_states.keys()]
    random.shuffle(members)
    team_size = int(len(members) / no_teams + 0.5)
    teams_string = "Teams:\n"
    for i in range(no_teams):
        team = members[i * team_size : (i + 1) * team_size]
        teams_string += "["
        for j, u in enumerate(team):
            teams_string += u.mention + ("," if j < len(team) - 1 else "")
            await u.move_to(voice_channels[i])
        teams_string += "]\n"
    await channel.send(teams_string)


def get_help():
    text = "Available commands:"
    for com in COMMANDS:
        text += "\n\t\t:white_small_square: %s - %s" % (com, COMMANDS[com][2])
    text += "\n\nType `!k <command> --help` for more information!"
    return text


def get_usage(command):
    text = "usage: " + command + " "
    for t in COMMANDS[command][0]:
        text += "<" + t[0] + ":" + t[1].__name__ + ">"
    return text


async def parse_command(channel, author, command):
    args = command.split()
    if len(args) < 1:
        return "Please specify a command!\n%s" % get_help()
    if args[0] not in COMMANDS:
        return "Unknown command: %s" % args[0]
    elif len(args) - 1 < len(COMMANDS[args[0]][0]):
        return "Not enough arguments for command %s\n%s" % (args[0], get_usage(args[0]))
    else:
        expected_args = COMMANDS[args[0]][0]
        args = command.split(maxsplit=len(expected_args))
        result_args = {}
        for i, arg in enumerate(args[1:]):
            if arg == "-h" or arg == "--help":
                return get_usage(args[0])
            if i >= len(expected_args):
                break
            expected_arg = expected_args[i]
            try:
                result_args[expected_arg[0]] = (expected_arg[1])(arg)
            except ValueError as e:
                return "Invalid argument format '%s' for %s\n%s" % (arg, expected_arg[0], get_usage(args[0]))
            except Exception as e:
                return "Invalid argument: %s; expected %s\n%s" % (arg, expected_arg[0], get_usage(args[0]))
        await COMMANDS[args[0]][1](channel, author, result_args)
            

def format_pre(msg):
    return "```\n" + str(msg) + "\n```"


class DiscordClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents().all())

    async def on_ready(self):
        print("Logged in as %s" % self.user)

    async def on_message(self, message):
        if message.author == self.user:
            return
        print("Message from", message.author, ":", message.content)
        if message.content.startswith("!k"):
            try:
                result = await parse_command(message.channel, message.author, message.content[3: ])
                if result is not None:
                    await message.channel.send(result)
            except:
                traceback.print_exc()


client = DiscordClient()
client.run(TOKEN)
