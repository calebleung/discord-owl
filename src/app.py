import discord
from discord.ext import commands

import asyncio
import configparser
import json
import requests

STATES = ['PENDING', 'IN_PROGRESS', 'CONCLUDED']
#STATUS = ['LIVE', 'UPCOMING']

config = configparser.ConfigParser()
config.read('config')

description = '''Retrieve OWL info.'''
client = commands.Bot(command_prefix='!', description=description)

with open('assets/maps') as jsonMapData:
    mapData = json.load(jsonMapData)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await client.change_presence(game=discord.Game(name='!status & !next'))

@client.command()
async def status():
    data = getInfo('liveMatch')
    await client.say(embed=buildEmbed(data))

@client.command()
async def next():
    data = getInfo('nextMatch')
    await client.say(embed=buildEmbed(data))

def getInfo(matchType):
    data = {}
    matchData = getMatchData()

    if bool(matchData['data'][matchType]) is False:
        matchType = 'liveMatch'

    teams = [matchData['data'][matchType]['competitors'][0]['name'], matchData['data'][matchType]['competitors'][1]['name']]
    status = matchData['data'][matchType]['liveStatus']
    score = matchData['data'][matchType]['wins']

    data['teams'] = teams

    if status == 'LIVE':
        completed = 0
        inProgress = False

        for game in matchData['data'][matchType]['games']:
            if game['state'] == STATES[2]:
                completed += 1
            if game['state'] == STATES[1]:
                inProgress = True
                data['mapName'], data['mapThumb'] = getMapData(game['attributes']['map'])

        data['mapStatus'] = 'Map {}'.format(completed + 1)

        if not inProgress:
            if completed == 0:
                data['mapStatus'] = 'PRE-SHOW'
            elif completed == 2:
                data['mapStatus'] = 'HALF-TIME'
            else:
                data['mapStatus'] = 'WAITING'
            #elif completed >= 4:
            #    data['mapStatus'] = 'WRAPPING UP'

        data['mapStatus'] += ' ({} - {})'.format(score[0], score[1])

    else:
        data['mapName'] = '{}'.format(getTimeToMatch(matchData['data'][matchType]['timeToMatch']))
        data['mapThumb'] = 'https://blznav.akamaized.net/img/esports/esports-overwatch-36d8f7f486d363c1.png'
        data['mapStatus'] = 'COMING SOON'


    return data

def getTimeToMatch(ms):
    hours, minutes = divmod(divmod(divmod(ms, 1000)[0], 60)[0], 60)
    
    if hours == 0 and minutes == 0:
        timeToMatch = 'RIGHT NOW'
    else:
        timeToMatch = 'in {} hours {} minutes'.format(hours, minutes)

    return timeToMatch

def getMatchData():
    return json.loads(requests.get('https://api.overwatchleague.com/live-match').text)

def getMapData(mapName):
    for sMap in mapData:
        if mapName == sMap['id']:
            return (sMap['name']['en_US'], sMap['thumbnail'])

def buildEmbed(data):
    em = discord.Embed(title='{} vs {}'.format(data['teams'][0], data['teams'][1]), description='', url='https://www.twitch.tv/overwatchleague')
    em.set_author(name='Overwatch League', icon_url='https://blznav.akamaized.net/img/esports/esports-mobile-overwatch-ce8dd5ae960a11f8.png')
    em.add_field(name='{}'.format(data['mapStatus']), value='{}'.format(data['mapName']), inline=False)
    em.set_thumbnail(url='{}'.format(data['mapThumb']))

    return em

client.run(config['Discord']['token'])