import discord
from discord.ext import commands

import asyncio
import configparser
import datetime
import json
import requests
import time

STATES = ['PENDING', 'IN_PROGRESS', 'CONCLUDED']
#STATUS = ['LIVE', 'UPCOMING']

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
    await client.change_presence(game=discord.Game(name='!status !next !live'))  

@client.command()
async def goodbot():
    global goodBotCount
    goodBotCount += 1

    await client.say(u'Beep boop! \u2282((\u30FB\u25BD\u30FB))\u2283 *{}*'.format(goodBotCount))

@client.command()
async def status():
    data = getInfo('liveMatch')
    await client.say(embed=buildMatchEmbed(data))

@client.command()
async def next():
    data = getInfo('nextMatch')
    await client.say(embed=buildMatchEmbed(data))

@client.command()
async def live():
    data = getInfo('liveMatch')
    msg = await client.say(embed=buildMatchEmbed(data))

    rawJSON = getMatchData('liveMatch')
    try:
        await updateInfo(msg, rawJSON['liveStatus'])
    except KeyError:
        pass

async def updateInfo(msg, matchType):
    while matchType == 'LIVE':
        await asyncio.sleep(300)
        data = getInfo('liveMatch')
        await client.edit_message(msg, embed=buildMatchEmbed(data))

    await asyncio.sleep(3600)
    await client.delete_message(msg)


def getInfo(matchType):
    data = {}
    matchData = getMatchData(matchType)

    teams = [matchData['competitors'][0]['name'], matchData['competitors'][1]['name']]
    score = matchData['scores']

    try:
        status = matchData['liveStatus']
    except KeyError:
        status = 'NEXT WEEK'

    data['teams'] = teams

    data['mapName'] = 'GET HYPED!'
    data['mapThumb'] = 'https://blznav.akamaized.net/img/esports/esports-overwatch-36d8f7f486d363c1.png'

    if status == 'LIVE':
        completed = 0
        inProgress = False

        for game in matchData['games']:
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
            elif completed >= 4:
                if score[0]['value'] == score[1]['value']:
                    data['mapStatus'] = 'GOING TO OVERTIME'
                else:
                    data['mapStatus'] = 'WRAPPING UP'
                    winner = 0
                    if score[0]['value'] < score[1]['value']:
                        winner = 1
                    data['mapName'] = '{} wins!'.format(teams[winner])
            else:
                data['mapStatus'] = 'WAITING'

        data['mapStatus'] += ' ({} - {})'.format(score[0]['value'], score[1]['value'])
    elif status == 'UPCOMING':
        data['mapStatus'] = 'COMING SOON'
        data['mapName'] = '{}'.format(getTimeToMatch(matchData['timeToMatch']))
    else:
        data['mapStatus'] = 'COMING SOON'
        data['mapName'] = 'GET HYPED'

    return data

def getTimeToMatch(ms):
    hours, minutes = divmod(divmod(divmod(ms, 1000)[0], 60)[0], 60)
    
    if hours == 0 and minutes == 0:
        timeToMatch = 'COMING SOON'
    else:
        timeToMatch = 'in {} hours {} minutes'.format(hours, minutes)

    return timeToMatch

def getMatchData(matchType):
    matchData = json.loads(requests.get('https://api.overwatchleague.com/live-match').text)

    match = matchData['data'][matchType]

    if bool(matchData['data']['liveMatch']) is False:
        # Assuming liveMatch is only empty at the end of the week and not during the week prior to Weds
        global owlStage
        global owlWeek

        owlStage, owlWeek = getCurrentWeek()
        match = scheduleData['data']['stages'][owlStage]['weeks'][owlWeek]['matches'][0]

    if bool(match) is False:
        match = matchData['data']['liveMatch']

    return match

def getMapData(mapName):
    for sMap in mapData:
        if mapName == sMap['id']:
            return (sMap['name']['en_US'], sMap['thumbnail'])

def buildMatchEmbed(data):
    em = discord.Embed(title='{} vs {}'.format(data['teams'][0], data['teams'][1]), description='', url='https://www.twitch.tv/overwatchleague')
    em.set_author(name='Overwatch League', icon_url='https://blznav.akamaized.net/img/esports/esports-mobile-overwatch-ce8dd5ae960a11f8.png')
    em.add_field(name='{}'.format(data['mapStatus']), value='{}'.format(data['mapName']), inline=False)
    em.set_thumbnail(url='{}'.format(data['mapThumb']))
    em.set_footer(text='{}'.format(datetime.datetime.utcnow().strftime('%-I:%M:%S UTC')))

    return em

def getCurrentWeek():
    stages = scheduleData['data']['stages']
    currentUnixTime = int(time.time())
    currentStage = 0
    currentWeek = 0

    for i, stage in enumerate(stages):
        for j, week in enumerate(stage['weeks']):
            if currentUnixTime > week['startDate']/1000 and currentUnixTime < week['endDate']/1000:
                # We assume the 'id' will always be the same as the position in array
                currentStage = stage['id']
                if (datetime.datetime.fromtimestamp(week['endDate']/1000) - datetime.datetime.fromtimestamp(currentUnixTime)).total_seconds() > 172800:
                    currentWeek = week['id']
                else:
                    try:
                        currentWeek = stage['weeks'][j+1]['id']
                    except IndexError:
                        try:
                            currentStage = stages[i+1]['id']
                            currentWeek = 0
                        except IndexError:
                            currentStage = stage['id']
                            # The season is over!
    
    print('Stage {} - Week {}'.format(currentStage, currentWeek + 1))

    return (currentStage, currentWeek)

goodBotCount = 0

with open('assets/maps') as jsonMapData:
    mapData = json.load(jsonMapData)

with open('assets/schedule') as jsonScheduleData:
    scheduleData = json.load(jsonScheduleData)

owlStage, owlWeek = getCurrentWeek()

client.run(config['Discord']['token'])