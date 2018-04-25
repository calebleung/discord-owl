import discord
from discord.ext import commands

from asyncio_owl import ClientOWL

import asyncio
import configparser
import datetime
import json
import logging
import re
import time

ONE_DAY_IN_SECONDS = 86400
EIGHT_HOURS_IN_SECONDS = 28800

STATES = ['PENDING', 'IN_PROGRESS', 'CONCLUDED']
#STATUS = ['LIVE', 'UPCOMING']

config = configparser.ConfigParser()
config.read('config')

description = '''Retrieve OWL info.'''
logging.basicConfig(level=logging.INFO)

bot = commands.Bot(command_prefix='!!', description=description)
bot.goodbotCount = 0

bot.schedule = {}
bot.stage = {}
bot.week = {}
bot.match = 0
bot.secondsToNextMatch = 0
bot.waitingForNextMatch = False

bot.liveMatch = {}
bot.nextMatch = {}

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

async def background_getLiveMatch():
    async with ClientOWL(loop=asyncio.get_event_loop()) as owl:    
        matchData = await owl.live_match()
    while any(matchData['nextMatch']):
        print('looping',matchData['liveMatch']['timeToMatch'])
        
        await asyncio.sleep(30)
        async with ClientOWL(loop=asyncio.get_event_loop()) as owl:
            matchData = await owl.live_match()

async def background_waitForNextMatch():
    await asyncio.sleep(bot.secondsToNextMatch)
    bot.loop.create_task(background_getLiveMatch())         
    bot.waitingForNextMatch = False

async def background_getCurrentWeek():
    await bot.wait_until_ready()
    while not bot.is_closed():
        async with ClientOWL(loop=asyncio.get_event_loop()) as owl:
            bot.schedule = await owl.schedule()
            for i, stage in enumerate(bot.schedule):
                for j, week in enumerate(stage['weeks']):
                    for k, match in enumerate(week['matches']):
                        if int(match['startDateTS']/1000 - time.time()) > 0:
                            bot.stage = stage
                            bot.week = week
                            bot.secondsToNextMatch = int(match['startDateTS']/1000 - time.time())
                            print('Next: Stage {}, Week {}, Match {}: {}'.format(i, j+1, k+1, bot.secondsToNextMatch))
                            if bot.waitingForNextMatch is False:
                                if any(owl.live_match('nextMatch')):
                                    bot.loop.create_task(background_getLiveMatch())
                                else:
                                    bot.waitingForNextMatch = True
                                    bot.loop.create_task(background_waitForNextMatch())
                            return
            await asyncio.sleep(ONE_DAY_IN_SECONDS)

async def my_background_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        bot.goodbotCount += 1
        await channel.send(u'Beep boop! \u2282((\u30FB\u25BD\u30FB))\u2283 *{}*'.format(bot.goodbotCount))
        await asyncio.sleep(ONE_DAY_IN_SECONDS) # task runs every 60 seconds

@bot.command(aliases=['sch'])
async def schedule(ctx, stage=-1, week=-1):
    if stage == -1:
        stage = bot.stage['id']
    if week == -1:
        week = bot.week['id']
    else:
        week -= 1

    try:
        weeklySchedule = bot.schedule[stage]['weeks'][week]
    except IndexError:
        if bot.schedule[stage]['enabled'] is False:
            await ctx.send('**Bweeee**! Schedule for {} isn\'t live yet!'.format(bot.schedule[stage]['name']))
            return
        stage = bot.stage['id']
        week = bot.week['id']
        weeklySchedule = bot.schedule[stage]['weeks'][week]
        await ctx.send('*Zwee?* Could not find a matching stage/week combination!')
    
    prevMatchTime = weeklySchedule['matches'][0]['endDateTS']/1000
    matches = []
    day = ''

    try:
        for match in weeklySchedule['matches']:
            if (datetime.datetime.fromtimestamp(match['startDateTS']/1000) - datetime.datetime.fromtimestamp(prevMatchTime)).total_seconds() > EIGHT_HOURS_IN_SECONDS:
                matches.append(day)
                day = ''

            prevMatchTime = match['endDateTS']/1000
            teams = [match['competitors'][0]['name'], match['competitors'][1]['name']]

            if datetime.datetime.fromtimestamp(prevMatchTime) < datetime.datetime.utcnow():
                winner = 0
                if match['wins'][0] < match['wins'][1]:
                    winner = 1

                if match['state'] == STATES[2]:
                    teams[winner] = '**{}**'.format(teams[winner])

                day += '{} ( {} - {} ) {}\n'.format(teams[0], match['wins'][0], match['wins'][1], teams[1])
            else:
                day += '{} vs {}\n'.format(teams[0], teams[1])
        matches.append(day)
    except TypeError:
        # If 'competitors' are None, they aren't set for Title Matches at the end of Stages
        matches.append('Stage playoffs this week!')

    em = discord.Embed(title='Schedule for {} {}'.format(bot.schedule[stage]['name'], bot.schedule[stage]['weeks'][week]['name']), description='')
    em.set_author(name='Overwatch League', icon_url=config['Overwatch']['logo_icon'])

    for i, day in enumerate(matches):
        em.add_field(name='Day {}'.format(i+1), value='{}'.format(day), inline=True)

    em.set_thumbnail(url=config['Overwatch']['logo_thumbnail'])
    em.set_footer(text='{}'.format(datetime.datetime.utcnow().strftime('%-I:%M:%S UTC')))

    await ctx.send(embed=em)

@bot.command()
async def goodbot():
    bot.goodbotCount += 1

    msg = await ctx.send(u'Beep boop! \u2282((\u30FB\u25BD\u30FB))\u2283 *{}*'.format(bot.goodbotCount))

bot.loop.create_task(background_getCurrentWeek())
bot.run(config['Discord']['token'])