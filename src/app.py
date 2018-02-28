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
async def match(matchNum):
    data = getInfo(matchNum)
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

@client.command(aliases=['stage'])
async def schedule(*stageWeek):
    if len(stageWeek) == 0:
        await buildScheduleEmbed(owlStage, owlWeek)
    elif len(stageWeek) == 2:
        # We decrease the given week# by 1. We don't do this for Stage b/c of preseason
        adjustedWeek = int(stageWeek[1]) - 1
        await buildScheduleEmbed(int(stageWeek[0]), adjustedWeek)
    else:
        await client.say('**Bweeee**! Use `!schedule` or `!schedule <stage#> <week#>`')

async def buildScheduleEmbed(stage, week):
    # We increase the given week# by 1.
    adjustedWeek = week + 1
    data = getScheduleData(stage, week)

    if (len(data) == 0):
        await client.say('*Zwee?* Could not find a matching stage/week combination for stage {}/week {}'.format(stage, adjustedWeek))
    elif data[0] == 'say':
        await client.say(data[1])
    else:
        em = discord.Embed(title='Schedule for Stage {} Week {}'.format(stage, adjustedWeek), description='')
        em.set_author(name='Overwatch League', icon_url=config['Overwatch']['logo_icon'])

        for i, matches in enumerate(data):
            em.add_field(name='Day {}'.format(i+1), value='{}'.format(matches), inline=True)

        em.set_thumbnail(url=config['Overwatch']['logo_thumbnail'])
        em.set_footer(text='{}'.format(datetime.datetime.utcnow().strftime('%-I:%M:%S UTC')))

        await client.say(embed=em)

def getScheduleData(stage, week):
    try:
        data = []
        day = ''
        schedule = scheduleData['data']['stages'][stage]['weeks'][week]
        endDateTS = schedule['matches'][0]['endDateTS']/1000

        for match in schedule['matches']:
            # If next game is more than 8 hours away, it's scheduled for the next day
            if (datetime.datetime.fromtimestamp(match['startDateTS']/1000) - datetime.datetime.fromtimestamp(endDateTS)).total_seconds() > 28800:
                data.append(day)
                day = ''

            endDateTS = match['endDateTS']/1000
            teams = [match['competitors'][0]['name'], match['competitors'][1]['name']]

            if (datetime.datetime.fromtimestamp(match['startDateTS']/1000) < datetime.datetime.utcnow()):
                winner = 0
                if match['wins'][0] < match['wins'][1]:
                    winner = 1
                teams[winner] = '**{}**'.format(teams[winner])

                day += '{} ( {} - {} ) {}\n'.format(teams[0], match['wins'][0], match['wins'][1], teams[1])
            else:
                day += '{} vs {}\n'.format(teams[0], teams[1])

        data.append(day)
    except IndexError:
        try:
            # If the stage exists but aren't enabled...
            if (scheduleData['data']['stages'][stage]['enabled'] is False):
                return ('say', 'No information available for Stage {}: {}'.format(stage, scheduleData['data']['stages'][stage]['name']))
        except IndexError:
            pass
    except TypeError:
        # If 'competitors' are None, they aren't set for Title Matches at the end of Stages
        data.append('Additional matches this week.')

    return data

def getInfo(matchType):
    data = {}
    matchData = getMatchData(matchType)

    teams = [matchData['competitors'][0]['name'], matchData['competitors'][1]['name']]
    score = matchData['scores']
    winner = 0

    try:
        status = matchData['liveStatus']
    except KeyError:
        status = 'NOT LIVE'

    data['teams'] = teams

    data['matchScore'] = u'\ufeff'
    data['mapPoints'] = u'\ufeff'
    data['mapStatus'] = 'COMING SOON'
    data['mapName'] = u'\ufeff'
    data['mapThumb'] = config['Overwatch']['logo_thumbnail']
    data['url'] = 'https://www.twitch.tv/overwatchleague'

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
        data['matchScore'] = '{} - {}'.format(score[0]['value'], score[1]['value'])
        data['mapPoints'] = '{} - {}'.format(matchData['wins'][0], matchData['wins'][1])

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
                    if score[0]['value'] < score[1]['value']:
                        winner = 1
                    data['mapName'] = '{} wins!'.format(teams[winner])
            else:
                data['mapStatus'] = 'WAITING'
    elif status == 'UPCOMING':
        data['mapName'] = '{}'.format(getTimeToMatch(matchData['timeToMatch']))
    else:
        if matchData['state'] == STATES[2]:
            if score[0]['value'] < score[1]['value']:
                winner = 1
            data['mapStatus'] = '{} wins!'.format(teams[winner])
            data['mapName'] = '{} - {}'.format(score[0]['value'], score[1]['value'])
            data['mapThumb'] = matchData['competitors'][winner]['logo']
            data['url'] = 'https://overwatchleague.com/en-us/match/{}'.format(matchType)

    return data

def getTimeToMatch(ms):
    hours, minutes = divmod(divmod(divmod(ms, 1000)[0], 60)[0], 60)
    
    if hours == 0 and minutes == 0:
        timeToMatch = 'COMING SOON'
    else:
        timeToMatch = 'in {} hours {} minutes'.format(hours, minutes)

    return timeToMatch

def getMatchData(matchType):
    if matchType == 'liveMatch' or matchType == 'nextMatch':
        matchData = json.loads(requests.get('https://api.overwatchleague.com/live-match').text)

        match = matchData['data'][matchType]

        if bool(matchData['data']['liveMatch']) is False:
            # Assuming liveMatch is only empty at the end of the week and not during the week prior to Weds
            getCurrentWeek()
            match = scheduleData['data']['stages'][owlStage]['weeks'][owlWeek]['matches'][0]

        if bool(match) is False:
            match = matchData['data']['liveMatch']
    else:
        match = json.loads(requests.get('https://api.overwatchleague.com/matches/{}'.format(int(matchType))).text)

    return match

def getMapData(mapName):
    for sMap in mapData:
        if mapName == sMap['id']:
            return (sMap['name']['en_US'], sMap['thumbnail'])

def buildMatchEmbed(data):
    em = discord.Embed(title='{} vs {}'.format(data['teams'][0], data['teams'][1]), description='', url=data['url'])
    em.set_author(name='Overwatch League', icon_url=config['Overwatch']['logo_icon'])
    em.add_field(name='{}'.format(data['mapStatus']), value='{}'.format(data['mapName']), inline=True)
    em.add_field(name='{}'.format(data['matchScore']), value='{}'.format(data['mapPoints']), inline=True)
    em.set_thumbnail(url='{}'.format(data['mapThumb']))
    em.set_footer(text='{}'.format(datetime.datetime.utcnow().strftime('%-I:%M:%S UTC')))

    return em

def getCurrentWeek():
    global owlStage
    global owlWeek

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

    owlStage, owlWeek = (currentStage, currentWeek)

goodBotCount = 0

with open('assets/maps') as jsonMapData:
    mapData = json.load(jsonMapData)

with open('assets/schedule') as jsonScheduleData:
    scheduleData = json.load(jsonScheduleData)

getCurrentWeek()

client.run(config['Discord']['token'])