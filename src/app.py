import discord
from discord.ext import commands

import asyncio
import configparser
import json
import requests

STATES = ['PENDING', 'IN_PROGRESS', 'CONCLUDED']

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
    await client.say(getInfo('liveMatch'))

@client.command()
async def next():
    await client.say(getInfo('nextMatch'))

@client.command()
async def test():
    data = {}
    data['teams'] = ['Boston Uprising', 'Philadelphia Fusion']
    data['mapName'], data['mapThumb'] = getMapData('kings-row')
    data['completedMaps'] = 2

    await client.say(embed=buildEmbed(data))

def getInfo(matchType):
    data = {}
    matchData = getMatch()

    if bool(matchData['data'][matchType]) is False:
        matchType = 'liveMatch'

    teams = [matchData['data'][matchType]['competitors'][0]['name'], matchData['data'][matchType]['competitors'][1]['name']]
    status = matchData['data'][matchType]['liveStatus']

    #msg = await client.say('%s vs %s is %s' % (teams[0], teams[1], status))
    msg = '%s vs %s is %s' % (teams[0], teams[1], status)

    data['teams'] = teams

    if status == 'LIVE':
        completed = 0
        inProgress = False

        for game in matchData['data'][matchType]['games']:
            if game['state'] == STATES[2]:
                completed += 1
            if game['state'] == STATES[1]:
                inProgress = True
                #await client.edit_message(msg, '%s on %s' % (msg.content, game['attributes']['map']).replace('-',' ').title())
                msg += ' on %s' % game['attributes']['map'].replace('-',' ').title()
                data['mapName'], data['mapThumb'] = getMapData(game['attributes']['map'])

        if not inProgress:
            if completed == 2:
                msg += ' at HALF-TIME'
            if completed >= 4:
                msg += ' WRAPPING UP'

        data['completedMaps'] = completed

    return msg

def getMatch():
    return json.loads(requests.get('https://api.overwatchleague.com/live-match').text)

def getMapData(mapName):
    for sMap in mapData:
        if mapName == sMap['id']:
            return (sMap['name']['en_US'], sMap['thumbnail'])

def buildEmbed(data):
    em = discord.Embed(title='{} vs {}'.format(data['teams'][0], data['teams'][1]), description='')
    em.set_author(name='Overwatch League', icon_url='https://blznav.akamaized.net/img/esports/esports-mobile-overwatch-ce8dd5ae960a11f8.png')
    em.add_field(name='Map {}'.format(data['completedMaps'] + 1), value='{}'.format(data['mapName']), inline=False)
    #em.add_field(name="Field2", value="hi2", inline=False)
    #em.set_image(url=client.user.default_avatar_url)
    em.set_thumbnail(url='{}'.format(data['mapThumb']))
    #em.set_footer(text="Hello World", icon_url=client.user.default_avatar_url)

    return em

client.run(config['Discord']['token'])