import discord
from discord.ext import commands

import asyncio
import configparser
import json
import requests

config = configparser.ConfigParser()
config.read('config')

description = '''Retrieve OWL info.'''
client = commands.Bot(command_prefix='!', description=description)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await client.change_presence(game=discord.Game(name='!status & !next'))

@client.command()
async def status():
    await client.say(getMatch('liveMatch'))

@client.command()
async def next():
    await client.say(getMatch('nextMatch'))

def getMatch(matchType):
    res = getJSON()
    teams = [res['data'][matchType]['competitors'][0]['name'], res['data'][matchType]['competitors'][1]['name']]
    status = res['data'][matchType]['liveStatus']

    #msg = await client.say('%s vs %s is %s' % (teams[0], teams[1], status))
    msg = '%s vs %s is %s' % (teams[0], teams[1], status)

    if status == 'LIVE':
        STATES = ['PENDING', 'IN_PROGRESS', 'CONCLUDED']
        completed = 0
        inProgress = False

        for game in res['data'][matchType]['games']:
            if game['state'] == STATES[2]:
                completed += 1
            if game['state'] == STATES[1]:
                inProgress = True
                #await client.edit_message(msg, '%s on %s' % (msg.content, game['attributes']['map']).replace('-',' ').title())
                msg += ' on %s' % game['attributes']['map'].replace('-',' ').title()

        if not inProgress and completed == 2:
            msg += ' at HALF-TIME'

    return msg

def getJSON():
    return json.loads(requests.get('https://api.overwatchleague.com/live-match').text)


client.run(config['Discord']['token'])