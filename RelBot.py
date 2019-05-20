import discord
from discord.ext import commands
import asyncio
import aiohttp
import json
import traceback
import sys
import PIL
from PIL import Image, ImageDraw, ImageFont
import base64
import io
import concurrent.futures
import os
import random
import time
import math
import re
from jsonschema import validate
import gspread
import gspread_formatting
import copy
import colorsys
import shutil
import requests
from oauth2client.service_account import ServiceAccountCredentials
from functools import partial
#from concurrent.futures import ThreadPoolExecutor

client = commands.Bot(command_prefix = '!')
token = "InsertTokenHere"
gscope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
gcreds = ServiceAccountCredentials.from_json_keyfile_name('relbot_secrets.json', gscope)
gclient = gspread.Client(auth=gcreds)

print("Booting up!")


try:
    with open('charts.json', 'r+') as file:
        charts = json.load(file)
except:
    try:
        with open('backup.json', 'r+') as file:
            charts = json.load(file)
    except:
        charts = {}
        print("failed")



@client.event           #upon joining a server, create a blank entry for it
async def on_server_join(server):
    global charts
    if server.id in charts.keys():
        charts.pop(server.id) #this should never happen - but in case there is garbage, better remove it
    charts[server.id] = {
                    "charts": {},
                    "log": None,
                    "sheet": None
    }

@client.event           #upon getting removed from a server, delete its entries
async def on_server_remove(server):
    global charts
    if server.id in charts.keys():
        if charts[server.id]["sheet"]!=None:
            gclient.login()
            gclient.del_spreadsheet(gclient.open_by_url(charts[server.id]["sheet"]).id)
        charts.pop(server.id) #this is why stuff above *should* be redundant

@client.event
async def on_error(event, *args, **kwargs):
    global charts
    trace = traceback.format_exc()
    print(trace)
    destiny = args[0].server.get_channel(charts[args[0].server.id]["log"])
    if destiny == None: destiny = args[0].server
    try:
        embed = discord.Embed(
                    title ="oopsie woopsie uwu i broke",
                    description = "`"+trace+"`",
                    colour = discord.Color.purple()
                )
        embed.set_author(name = ars[0].server.me.name, icon_url = args[0].server.me.avatar_url)
        embed.set_footer(text="Better bother Lance about this.")
        await client.send_message(destiny, embed=embed)
    except:
        #well, this is *really* bad.
        #write it to the logs, coupled with what failed here
        try:
            with open("errlog.txt", "r+") as log:
                log.seek(0, 2)
                log.write("\n" + trace + "\n!\n" + traceback.format_exc())
        except:
            with open("errlog.txt", "w") as log:
                log.seek(0, 2)
                log.write("\n" + trace + "\n!\n" + traceback.format_exc())



@client.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.CommandNotFound):
            return
    text = traceback.format_exception(type(error), error, error.__traceback__)
    text = "".join(text)
    print(text)
    global charts
    destiny = ctx.message.server.get_channel(charts[ctx.message.server.id]["log"])
    if destiny == None: destiny = ctx.message.server
    try:
        embed = discord.Embed(
                    title ="oopsie woopsie uwu i broke",
                    description = "`"+text+"`",
                    colour = discord.Color.purple()
                )
        embed.set_author(name = ctx.message.server.me.name, icon_url = ctx.message.server.me.avatar_url)
        embed.set_footer(text="Better bother Lance about this.")
        await client.send_message(destiny, embed=embed)
    except:
        #well, this is *really* bad.
        #write it to the logs, coupled with what failed here
        with open("errlog.txt", "r+") as log:
            log.seek(0, 2)
            log.write("\n" + text + "\n!\n" + traceback.format_exc())
        pass

##@client.event
##async def on_message(message):   #no private message handling!
##    if message.channel.is_private == False:
##        client.process_commands(message)


@client.command(pass_context = True) #command to have the bot send a OAuth link
async def summon(ctx):
    await client.send_message(ctx.message.author,
    "Here you are! Click this link to invite me to elsewhere.\n" +
    "https://discordapp.com/oauth2/authorize?client_id=538417547108941844&scope=bot&permissions=51264")

@client.command(pass_context = True)
async def exile(ctx):        #orders the bot to leave the server
    server = ctx.message.server
    if ctx.message.author != ctx.message.server.owner: #respond to server owners only
        return
    embed = discord.Embed(     #make a pretty message first
                    title ="Confirm exile?",
                    description = "This will remove me from this server and"+
                    " delete any and all charts you have saved.\n"+
                    "Are you sure you wish to exile me?",
                    colour = discord.Color.purple()
                )
    embed.set_footer(text="Respond by pressing one of the reactions below within 30 seconds.")
    embed.set_author(name = server.me.name, icon_url = server.me.avatar_url)

    #send it over, and apply reactions to it
    msg = await client.send_message(ctx.message.channel, embed=embed)
    await client.add_reaction(msg, '✅')
    await client.add_reaction(msg, '❌')

    #wait for 30 seconds for response
    res = await client.wait_for_reaction(['✅','❌'], message=msg, timeout=30, user=ctx.message.author)

    if res == None:
        await client.remove_reaction(msg, '✅', server.me)
        await client.remove_reaction(msg, '❌', server.me)
        await client.add_reaction(msg, "⏰")
    if res.reaction.emoji == '❌':
        await client.remove_reaction(msg, '✅', server.me)
        await client.remove_reaction(msg, '❌', server.me)
    if res.reaction.emoji == '✅':
        await client.leave_server(ctx.message.server)


@client.command(pass_context = True)
async def create_chart(ctx, name = None):         #creates a blank chart
    server = ctx.message.server.id
    global charts
    if name == None:
        await client.send_message(ctx.message.channel, "Please input the name for your chart!")
        return
    name = str(name)
    if name in charts[server]["charts"].keys():      #make sure one doesn't exist already
        await client.send_message(ctx.message.channel, "A chart with this name already exists!")
        return
    if len(ctx.message.attachments) == 0:
        charts[server]["charts"][name]={
            "people": {},
            "keys": {},
            "owner": ctx.message.author.id,
            "lock" : False,
            "auto" : False
        }
        await client.send_message(ctx.message.channel, "Blank chart named '" + name + "' created!")
    else:
        async with aiohttp.ClientSession() as ses:
            async with ses.get(ctx.message.attachments[0]['url']) as resp:
                f = await resp.text()
        try:
            f = json.loads(f)
        except:
            await client.send_message(ctx.message.channel, "Chart creation failed! Your file may be broken.")
        t = valid(f, "chart")
        if not isinstance(t, Exception):
            charts[server]["charts"][name] = f
            await client.send_message(ctx.message.channel, "Chart '"+name+"' loaded! Pruned " + str(t) + " invalid entries.")
        else:
            out = io.BytesIO(str(t).encode('utf-8'))
            out.seek(0)
            await client.send_file(ctx.message.channel, out, filename = "error_log.txt", content = "Chart validation failed! Here are the error logs:")
            out.close()

    with open('charts.json', 'w') as file:    #save it
        json.dump(charts, file)

@client.command(pass_context = True)
async def lock(ctx, chart = None, value = None):
    server = ctx.message.server.id
    global charts
    if chart == None:
        await client.send_message(ctx.message.channel, "Please input the name of the chart to check, followed by 'True' or 'False' if you wish to change the lock.")
        return
    if not chart in charts[server]["charts"].keys():  #make sure it exists
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
    if value == None:
        text = "The chart is "
        if charts[server]["charts"][chart]["lock"]:
            text += "locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!"
        else:
            text += "not locked!"
        await client.send_message(ctx.message.channel, text)
    else:
        if ctx.message.author.id != charts[server]["charts"][chart]["owner"] and ctx.message.author != ctx.message.server.owner:
            await client.send_message(ctx.message.channel, "Only the chart owner or server owner can set locks on a chart!")
            return
        value = value.lower()
        if value == "true":
            charts[server]["charts"][chart]["lock"] = True
            await client.send_message(ctx.message.channel, "This chart is now locked!")
        elif value == "false":
            charts[server]["charts"][chart]["lock"] = False
            await client.send_message(ctx.message.channel, "This chart is now unlocked!")
        else:
            await client.send_message(ctx.message.channel, "Invalid value! 'True' or 'False' only, please, with any case.")
            return
        with open('charts.json', 'w') as file:
            json.dump(charts, file)

@client.command(pass_context = True)
async def spreadsheet(ctx):
    server = ctx.message.server.id
    global charts
    await client.send_message(ctx.message.channel, "You may find this server's charts on:\n"+charts[server]["sheet"])


@client.command(pass_context = True)
async def refresh(ctx):
    server = ctx.message.server.id
    global charts
    if not server in charts.keys():
        charts[server]={
                    "charts": {},
                    "log": None,
                    "sheet": None
        }
        await client.send_message(ctx.message.channel, "Server readded!")
    else:
        await client.send_message(ctx.message.channel, "Server is already logged!")

@client.command(pass_context = True)
async def delete_chart(ctx, name = None):           #removes a chart
    server = ctx.message.server.id
    global charts
    if name == None:
        await client.send_message(ctx.message.channel, "Please input the name of the chart to be deleted!")
        return
    name = str(name)
    if not name in charts[server]["charts"].keys():  #make sure it exists
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
    if charts[server]["charts"][name]["lock"] and ctx.message.author.id not in (charts[server]["charts"][name]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
        return
    else:
        charts[server]["charts"].pop(name)
        with open('charts.json', 'w') as file:    #save it
            json.dump(charts, file)
        await client.send_message(ctx.message.channel, "Chart '" + name + "' removed!")
        if charts[server]["sheet"] != None:
            gclient.login()
            shobj = gclient.open_by_url(charts[server]["sheet"])
            if len(shobj.worksheets())==1:
                gclient.del_spreadsheet(shobj.id)
                charts[server]["sheet"] = None
                await client.send_message(ctx.message.channel, "All published charts removed; spreadsheet deleted.")
                with open('charts.json', 'w') as file:    #save it
                    json.dump(charts, file)
            elif shobj.worksheet(name) != None:
                shobj.del_worksheet(shobj.worksheet(name))


@client.command(pass_context = True)
async def add_key(ctx, chart = None, keyname = None, keycolor = None):  #adds a key to a chart
   server = ctx.message.server.id             #example: !add_key chart1 hate 23af45
   global charts
   if chart == None or keyname == None or keycolor == None:
        await client.send_message(ctx.message.channel, "Invalid agruments! Please input the chart name, the key name and the key color, in that order.")
        return
   chart = str(chart)
   keyname = str(keyname)
   keycolor = str(keycolor)
   if keyname.startswith('#'): keyname = keyname[1:6]
   if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
   if charts[server]["charts"][chart]["lock"] and ctx.message.author.id not in (charts[server]["charts"][chart]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
        return
   if len(list([c for c in keycolor.lower() if c in "0123456789abcdef"]))!=6:
        await client.send_message(ctx.message.channel, "Invalid color code! Please stick to RGB.")
        return
   if keyname in charts[server]["charts"][chart]["keys"].keys():
        await client.send_message(ctx.message.channel, "This key already exists!")
        return
   if keycolor in charts[server]["charts"][chart]["keys"].values():
        await client.send_message(ctx.message.channel, "A key with this color already exists!")
        return
    #checks done
   charts[server]["charts"][chart]["keys"][keyname] = keycolor.lower()
   with open('charts.json', 'w') as file:    #save it
        json.dump(charts, file)
   await client.send_message(ctx.message.channel, "Key added!")
   return

@client.command(pass_context = True)
async def delete_key(ctx, chart = None, keyname = None):     #removes a key from chart along with any rels using it
   server = ctx.message.server.id             #example: !add_key chart1 hate 23af45
   global charts
   if chart == None or keyname == None:
        await client.send_message(ctx.message.channel, "Invalid arguments! Please input the chart name and the name of the key to be deleted, in that order.")
        return
   chart = str(chart)
   keyname = str(keyname)
   if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
   if charts[server]["charts"][chart]["lock"] and ctx.message.author.id not in (charts[server]["charts"][chart]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
        return
   if not keyname in charts[server]["charts"][chart]["keys"].keys():
        await client.send_message(ctx.message.channel, "No such key exists!")
        return
    #checks done
   charts[server]["charts"][chart]["keys"].pop(keyname)          #remove key from keychart
   for value in charts[server]["charts"][chart]["people"].values():  #list through every person in chart
        value["rels"] = {k: v for k,v in value["rels"].items() if v["key"] != keyname}  #remove all mentions of this key through magic of list comprehenzion
   with open('charts.json', 'w') as file:    #save it
        json.dump(charts, file)
   await client.send_message(ctx.message.channel, "Key removed!")
   return

@client.command(pass_context = True)
async def add_person(ctx, chart = None, name = None):       #adds person to chart (with blank rels)
   server = ctx.message.server.id             #example: !add_person chart1 Lance
   global charts
   if chart == None or name == None:
        await client.send_message(ctx.message.channel, "Invalid arguments! Please input the name of the chart and the name of the person to record, in that order.")
        return
   chart = str(chart)
   name = str(name)
   if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
   if charts[server]["charts"][chart]["lock"] and ctx.message.author.id not in (charts[server]["charts"][chart]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
        return
   if name in charts[server]["charts"][chart]["people"].keys():
        await client.send_message(ctx.message.channel, "This person already exists!")
        return
   #checks done
   charts[server]["charts"][chart]["people"][name] = {
                                        "rels": {},
                                        "avatar": None,
                                        "motto" : None
                                        }
   with open('charts.json', 'w') as file:    #save it
        json.dump(charts, file)
   await client.send_message(ctx.message.channel, "Person added!")
   return

@client.command(pass_context = True)
async def add_people(ctx, chart, *args):
   server = ctx.message.server.id             #example: !remove_person chart1 Lance
   global charts
   if chart == None:
        await client.send_message(ctx.message.channel, "Please input the name of the chart, then any number of names to add to it.")
        return
   chart = str(chart)
   n = 0
   if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
   if charts[server]["charts"][chart]["lock"] and ctx.message.author.id not in (charts[server]["charts"][chart]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
        return
   for name in args:
        name = str(name)
        if name in charts[server]["charts"][chart]["people"].keys():
            await client.send_message(ctx.message.channel, "Skipped "+name+": this person already exists!")
            continue
        charts[server]["charts"][chart]["people"][name] = {
                                        "rels": {},
                                        "avatar": None,
                                        "motto" : None
                                        }
        n+=1
   await client.send_message(ctx.message.channel, "Added "+str(n)+" people!")
   with open('charts.json', 'w') as file:    #save it
        json.dump(charts, file)

@client.command(pass_context = True)
async def delete_people(ctx, chart = None, *args):
   server = ctx.message.server.id             #example: !remove_person chart1 Lance
   global charts
   if chart == None:
        await client.send_message(ctx.message.channel, "Please input the name of the chart, then any number of names to be deleted from it.")
        return
   chart = str(chart)
   n = 0
   if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
   if charts[server]["charts"][chart]["lock"] and ctx.message.author.id not in (charts[server]["charts"][chart]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
        return
   for name in args:
        name = str(name)
        if not name in charts[server]["charts"][chart]["people"].keys():
            await client.send_message(ctx.message.channel, "Skipped "+name+": no such person exists!")
            continue
        charts[server]["charts"][chart]["people"].pop(name)
        n+=1
   for person, value in charts[server]["charts"][chart]["people"].items():
        if value["rels"] != None: value["rels"] = {k: v for k,v in value["rels"].items() if k in charts[server]["charts"][chart]["people"].keys()}
   await client.send_message(ctx.message.channel, "Removed "+str(n)+" people!")
   with open('charts.json', 'w') as file:    #save it
        json.dump(charts, file)


@client.command(pass_context = True)
async def delete_person(ctx, chart = None, name = None):    #removes person from chart along with any rels to him
   server = ctx.message.server.id             #example: !remove_person chart1 Lance
   global charts
   if chart == None or name == None:
        await client.send_message(ctx.message.channel, "Invalid arguments! Please input the name of the chart and the name of the person to remove, in that order.")
        return
   chart = str(chart)
   name = str(name)
   if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
   if charts[server]["charts"][chart]["lock"] and ctx.message.author.id not in (charts[server]["charts"][chart]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
        return
   if not name in charts[server]["charts"][chart]["people"].keys():
        await client.send_message(ctx.message.channel, "Found no person with this name!")
        return
   #checks done
   charts[server]["charts"][chart]["people"].pop(name)   #delete person's entry
   for person, value in charts[server]["charts"][chart]["people"].items():
        if value["rels"] != None: value["rels"] = {k: v for k,v in value["rels"].items() if k in charts[server]["charts"][chart]["people"].keys()}  #remove all mentions of this person through magic of list comprehenzion
   with open('charts.json', 'w') as file:    #save it
        json.dump(charts, file)
   await client.send_message(ctx.message.channel, "Person removed!")
   return

@client.command(pass_context = True)
async def edit_rel(ctx, chart = None, source = None, target = None, key = None, desc = None): #sets a person's rel towards another
   server = ctx.message.server.id             #example: !edit_rel chart1 Lance Lance2 hate
   global charts
   if chart == None or source == None or target == None:
        await client.send_message(ctx.message.channel, "Invalid arguments! Please input the name of the chart, the name of the source, and the name of the target, followed by the key name and relationship description (or neither to remove the link).")
        return
   chart = str(chart)
   source = str(source)
   target = str(target)
   key = str(key)
   if desc != None: desc = str(desc)
   if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
   if charts[server]["charts"][chart]["lock"] and ctx.message.author.id not in (charts[server]["charts"][chart]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
        return
   if not source in charts[server]["charts"][chart]["people"].keys():
        await client.send_message(ctx.message.channel, "Found no source with this name!")
        return
   if not target in charts[server]["charts"][chart]["people"].keys():
        await client.send_message(ctx.message.channel, "Found no target with this name!")
        return
   if not (key in charts[server]["charts"][chart]["keys"].keys() or key == None):
        await client.send_message(ctx.message.channel, "No such key exists!")
        return
   if source == target:
        await client.send_message(ctx.message.channel, "Please do not make relationships from a person to the same person, that is just plain weird.")
        return
    #checks done
   if key == None: charts[server]["charts"][chart]["people"][source]["rels"].pop(target, None)
   else: charts[server]["charts"][chart]["people"][source]["rels"][target] = {
                                                                        "desc" : desc, "key" : key
   }
   with open('charts.json', 'w') as file:    #save it
        json.dump(charts, file)
   await client.send_message(ctx.message.channel, "Relationship edited!")
   return

@client.command(pass_context = True)
async def assign(ctx):
   server = ctx.message.server.id
   global charts
   if ctx.message.author != ctx.message.server.owner: #respond to server owners only
    return
   charts[server]["log"] = ctx.message.channel.id
   await client.send_message(ctx.message.channel, "Channel assigned! Error reports will be mailed here, should any arise.")
   with open('charts.json', 'w') as file:    #save it
        json.dump(charts, file)




@client.command(pass_context = True)
async def validate_chart(ctx, name = None):
    server = ctx.message.server.id
    global charts
    if name == None:
        n = valid(charts[server], "server")
        if not isinstance(n, Exception):
            await client.send_message(ctx.message.channel, "Server logs validated! Pruned " + str(n) + " invalid entries.")
        else:
            await client.send_message(ctx.message.channel, "Server validation failed:\n`" + str(n) + "`")
    else:
        name = str(name)
        if not name in charts[server]["charts"].keys():
            await client.send_message(ctx.message.channel, "Found no chart with this name!")
            return
        else:
            n = valid(charts[server]["charts"][name], "chart")
            if not isinstance(n, Exception):
                await client.send_message(ctx.message.channel, "Chart validated! Pruned " + str(n) + " invalid entries.")
            else:
                out = io.BytesIO(str(n).encode('utf-8'))
                out.seek(0)
                await client.send_file(ctx.message.channel, out, filename = "error_log.txt", content = "Chart validation failed! Here are the error logs:")
                out.close()


@client.command(pass_context = True)
async def set_avatar(ctx, chart = None, target = None): #updates avatar with file provided in message, or deletes avatar if there is none

   server = ctx.message.server.id
   global charts
   if chart == None or target == None:
        await client.send_message(ctx.message.channel, "Invalid arguments! Please input the name of the chart and the name of the avatar holder, in that order.")
        return
   chart = str(chart)
   target = str(target)
   if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
   if charts[server]["charts"][chart]["lock"] and ctx.message.author.id not in (charts[server]["charts"][chart]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
        return
   if not target in charts[server]["charts"][chart]["people"].keys():
        await client.send_message(ctx.message.channel, "Found no person with this name!")
        return
   #checks done
   if len(ctx.message.attachments) == 0:    #if there are no attachments, delete the one present
        charts[server]["charts"][chart]["people"][target]["avatar"] = None
        await client.send_message(ctx.message.channel, "Image removed.")
   else:
        if ctx.message.attachments[0]['height'] == ctx.message.attachments[0]['width']:    #otherwise download the first one
            async with aiohttp.ClientSession() as ses:
                async with ses.get(ctx.message.attachments[0]['proxy_url']) as r:
                    img = await r.read()
            img = io.BytesIO(img)
            img = PIL.Image.open(img).resize((128, 128), PIL.Image.BICUBIC)
            res = io.BytesIO()
            img.save(server+"_"+chart+"_"+target+".png", "PNG")
            charts[server]["charts"][chart]["people"][target]["avatar"] = server+"_"+chart+"_"+target+".png"   #and save it in the json
            await client.send_message(ctx.message.channel, "Image updated!")
            with open('charts.json', 'w') as file:    #save it
                json.dump(charts, file)
        else:
            await client.send_message(ctx.message.channel, "Hark! Your image is not square enough. Please crop it for convenience.")
            return


@client.command(pass_context = True)
async def get_avatar(ctx, chart = None, target = None):
    server = ctx.message.server.id
    global charts
    if chart == None or target == None:
        await client.send_message(ctx.message.channel, "Invalid arguments! Please input the name of the chart and the name of the avatar holder, in that order.")
        return
    chart = str(chart)
    target = str(target)
    if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
    if not target in charts[server]["charts"][chart]["people"].keys():
        await client.send_message(ctx.message.channel, "Found no person with this name!")
        return
    if charts[server]["charts"][chart]["people"][target]["avatar"] == None:
        await client.send_message(ctx.message.channel, "This person has no avatar!")
        return

    if charts[server]["charts"][chart]["people"][target]["avatar"] not in [f for f in os.listdir('.') if os.path.isfile(f)]:
        await client.send_message(ctx.message.channel, "Failed to load avatar! Avatar has been blanked; please reupload.")
        charts[server]["charts"][chart]["people"][target]["avatar"] = None
        with open('charts.json', 'w') as file:    #save it
                json.dump(charts, file)
        return
    else:
        await client.send_file(ctx.message.channel, charts[server]["charts"][chart]["people"][target]["avatar"], filename = "avatar_"+target+".png", content = "Avatar retrieved!")




@client.command(pass_context = True)
async def send_json(ctx, arg = None):
    server = ctx.message.server.id
    global charts
    if arg != None: arg = str(arg)
    if arg in charts[server]["charts"].keys():
        out = io.BytesIO()
        out.write(json.dumps(charts[server]["charts"][arg]).encode('utf-8'))
        out.seek(0)
        await client.send_file(ctx.message.channel, out, filename = arg+".json", content = "Chart "+arg+" in file form:")
        out.close()
        return
    elif arg == None:
        out = io.BytesIO()
        out.write(json.dumps(charts[server]).encode('utf-8'))
        out.seek(0)
        await client.send_file(ctx.message.channel, out, filename = arg+".json", content = "Full server chart logs:")
        out.close()
        return
    else:
        await client.send_message(ctx.message.channel, "No such chart found!")


@client.command(pass_context = True)
async def send_backup_json(ctx, arg = None):
    server = ctx.message.server.id
    if arg!= None: arg = str(arg)
    with open('backup.json') as file:
        charts = json.load(file)
    if arg in charts[server]["charts"].keys():
        out = io.BytesIO()
        out.write(json.dumps(charts[server]["charts"][arg]).encode('utf-8'))
        out.seek(0)
        await client.send_file(ctx.message.channel, out, filename = arg+".json", content = "Chart "+arg+" in file form:")
        out.close()
        return
    elif arg == None:
        out = io.BytesIO()
        out.write(json.dumps(charts[server]).encode('utf-8'))
        out.seek(0)
        await client.send_file(ctx.message.channel, out, filename = arg+".json", content = "Full server chart logs:")
        out.close()
        return
    else:
        await client.send_message(ctx.message.channel, "No such chart found!")

@client.command(pass_context = True)
async def autopublish(ctx, chart = None, value = None):
    server = ctx.message.server.id
    global charts
    if chart == None:
        await client.send_message(ctx.message.channel, "Please input the name of the chart to check, followed by 'True' or 'False' if you wish to change the setting.")
        return
    if not chart in charts[server]["charts"].keys():  #make sure it exists
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
    if value == None:
        if charts[server]["charts"][chart]["auto"]:
            text = "Autopublishing is active!"
        else:
            text = "Autopublishing is not active!"
        await client.send_message(ctx.message.channel, text)
    else:
        if charts[server]["charts"][chart]["lock"] and ctx.message.author.id not in (charts[server]["charts"][chart]["owner"], ctx.message.server.owner.id):
            await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
            return
        value = value.lower()
        if value == "true":
            charts[server]["charts"][chart]["auto"] = True
            await client.send_message(ctx.message.channel, "Autopublishing enabled!")
        elif value == "false":
            charts[server]["charts"][chart]["auto"] = False
            await client.send_message(ctx.message.channel, "Autopublishing disabled!")
        else:
            await client.send_message(ctx.message.channel, "Invalid value! 'True' or 'False' only, please, with any case.")
            return
        with open('charts.json', 'w') as file:
            json.dump(charts, file)

@client.command(pass_context = True)
async def use_backup(ctx, mode = None, chart = None):
    server = ctx.message.server.id
    me = ctx.message.server.me
    if mode == None:
        await client.send_message(ctx.message.channel, "Please input either 'chart' or 'server' (for server owners only), then the name of the chart, in that order.")
        return
    mode = str(mode).lower()
    global charts
    if len(ctx.message.attachments) == 0:
        await client.send_message(ctx.message.channel, "No attachment found!")
        return
    if mode not in ["server", "chart"]:
        await client.send_message(ctx.message.channel, "Invalid mode specified! Please choose 'chart' or 'server' (if you are the server owner).")
        return
    if (chart not in charts[server]["charts"].keys() or chart == None) and mode == "chart":
        await client.send_message(ctx.message.channel, "No such chart found!")
        return
    else:
        async with aiohttp.ClientSession() as ses:
            async with ses.get(ctx.message.attachments[0]['url']) as resp:
                f = await resp.text()
        try:
                f = json.loads(f)
        except:
            await client.send_message(ctx.message.channel, "Chart creation failed! Your file may be broken.")
            return
        t = valid(f, mode)
        if isinstance(t, Exception):
            out = io.BytesIO(str(t).encode('utf-8'))
            out.seek(0)
            await client.send_file(ctx.message.channel, out, filename = "error_log.txt", content = "Chart validation failed! Here are the error logs:")
            out.close()
            return
        if mode == "chart":
            charts[server]["charts"][chart]=copy.deepcopy(f)
            await client.send_message(ctx.message.channel, "Chart reuploaded!")
        else:
            msg = await client.send_message(ctx.message.channel, "This will rewrite all charts linked to this server. Are you sure?\n"+
            "(Keep in mind this might break other functions if your JSON is invalid; please only use those provided by the bot.)")
            await client.add_reaction(msg, '✅')
            await client.add_reaction(msg, '❌')

            #wait for 30 seconds for response
            res = await client.wait_for_reaction(['✅','❌'], message=msg, timeout=30, user=ctx.message.author)

            if res == None:
                await client.remove_reaction(msg, '✅', me)
                await client.remove_reaction(msg, '❌', me)
                await client.add_reaction(msg, "⏰")
            if res.reaction.emoji == '❌':
                await client.remove_reaction(msg, '✅', me)
                await client.remove_reaction(msg, '❌', me)
            if res.reaction.emoji == '✅':
                charts[server] = f
                await client.send_message(ctx.message.channel, "Backup loaded!")
                await client.remove_reaction(msg, '✅', me)
                await client.remove_reaction(msg, '❌', me)
        with open('charts.json', 'w') as file:    #save it
            json.dump(charts, file)


@client.command(pass_context = True)
async def reset(ctx):
    server = ctx.message.server.id
    me = ctx.message.server.me
    global charts
    if ctx.message.author != ctx.message.server.owner: #respond to server owners only
        return
    msg = await client.send_message(ctx.message.channel, "This will wipe all charts linked to this server. Are you sure?")
    await client.add_reaction(msg, '✅')
    await client.add_reaction(msg, '❌')

    #wait for 30 seconds for response
    res = await client.wait_for_reaction(['✅','❌'], message=msg, timeout=30, user=ctx.message.author)

    if res == None:
        await client.remove_reaction(msg, '✅', me)
        await client.remove_reaction(msg, '❌', me)
        await client.add_reaction(msg, "⏰")
    if res.reaction.emoji == '❌':
        await client.remove_reaction(msg, '✅', me)
        await client.remove_reaction(msg, '❌', me)
    if res.reaction.emoji == '✅':
        try:
            gclient.login()
            shobj = gclient.open_by_url(charts[server]["sheet"])
            gclient.del_spreadsheet(shobj.id)
        except: pass
        charts[server] = {
                    "charts": {},
                    "log": None,
                    "sheet": None
        }
        await client.send_message(ctx.message.channel, "Reset performed!")
        await client.remove_reaction(msg, '✅', me)
        await client.remove_reaction(msg, '❌', me)
    with open('charts.json', 'w') as file:    #save it
        json.dump(charts, file)

@client.command(pass_context = True)
async def view(ctx, chart = None, target = None):
    server = ctx.message.server.id
    global charts
    if chart == None:
        if len(charts[server]["charts"].keys()) == 0:
            await client.send_message(ctx.message.channel, "There are no charts saved for this server!")
        else:
            text = ', '.join(charts[server]["charts"].keys())
            if len(text) >= 1000:
                out = io.BytesIO()
                out.write(text.encode('utf-8'))
                out.seek(0)
                await client.send_file(ctx.message.channel, out, filename = "server_list.txt", content = "List of charts on this server:")
                out.close()
            else:
                await client.send_message(ctx.message.channel, "List of charts on this server: " + text)
        return
    elif chart != None and target == None:
        if chart not in charts[server]["charts"].keys():
            await client.send_message(ctx.message.channel, "No such chart found!")
            return
        else:
            text = "Owner: " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "\nLocked? : " + str(charts[server]["charts"][chart]["lock"])
            if "auto" in charts[server]["charts"][chart].keys(): text += "\nAutopublish: " + str(charts[server]["charts"][chart]["auto"])
            if charts[server]["charts"][chart]["keys"] != {}: text += "\nKeys: " + ", ".join(charts[server]["charts"][chart]["keys"].keys())
            if charts[server]["charts"][chart]["people"] != {} : text += '\nPeople: ' + ", ".join(charts[server]["charts"][chart]["people"].keys())
            if len(text) >= 1000:
                out = io.BytesIO()
                out.write(text.encode('utf-8'))
                out.seek(0)
                await client.send_file(ctx.message.channel, out, filename = chart+"_list.txt", content = "Contents of chart '" + chart + "':\n")
                out.close()
            else:
                await client.send_message(ctx.message.channel, "Contents of chart '" + chart + "':\n" + text)
        return
    elif chart != None and target != None:
        if chart not in charts[server]["charts"].keys():
            await client.send_message(ctx.message.channel, "No such chart found!")
            return
        if target not in charts[server]["charts"][chart]["people"].keys():
            await client.send_message(ctx.message.channel, "No such person found!")
            return
        else:
            entry = charts[server]["charts"][chart]["people"][target]
            text = ""
            if entry["motto"] != None: text += "Motto: \"" + entry["motto"] + "\"\n"
            if entry["rels"] != {}:
                text += "Relationships:\n "
                for name, rel in entry["rels"].items():
                    text += "- " + name + ": "+ rel["key"]
                    if rel["desc"] != None: text += " (\"" + rel["desc"] + "\")"
                    text+= "\n"
            if len(text) >= 1000:
                out = io.BytesIO()
                out.write(text.encode('utf-8'))
                out.seek(0)
                await client.send_file(ctx.message.channel, out, filename = target+"_list.txt", content = "Contents of " + target + "'s entry:\n")
                out.close()
            else:
                if text == "": await client.send_message(ctx.message.channel, target+"'s entry appears to be empty!")
                else: await client.send_message(ctx.message.channel, "Contents of "+target+"'s entry:\n" + text)
        return





@client.command(pass_context = True)
async def edit_motto(ctx, chart = None, name = None, motto = None):
    server = ctx.message.server.id
    if chart == None or name == None:
        await client.send_message(ctx.message.channel, "Invalid arguments! Please input the name of the chart and the name of the person to edit, in that order.")
        return
    global charts
    if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
    if charts[server]["charts"][chart]["lock"] and ctx.message.author.id not in (charts[server]["charts"][chart]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
        return
    if not name in charts[server]["charts"][chart]["people"].keys():
        await client.send_message(ctx.message.channel, "Found no person with this name!")
        return
    #checks done
    charts[server]["charts"][chart]["people"][name]["motto"] = motto
    if motto == None:
        await client.send_message(ctx.message.channel, "Motto deleted!")
    else: await client.send_message(ctx.message.channel, "Motto updated!")


@client.command(pass_context = True)
async def view_published(ctx):
    server = ctx.message.server.id
    global charts
    if charts[server]["sheet"]==None:
        await client.send_message(ctx.message.channel, "This server has not published any charts!")
        return
    else:
        gclient.login()
        shobj = gclient.open_by_url(charts[server]["sheet"])
        await client.send_message(ctx.message.channel, "List of published charts: "+', '.join([w.title for w in shobj.worksheets()]))


@client.command(pass_context = True)
async def internal_retrieve(ctx, key, sheet):
    if ctx.message.author.id not in ("548979869267132437", "190524109937967105"):
        return
    global charts
    key = str(key)
    sheet = str(sheet)
    try:
        gclient.login()
        shobj = gclient.open_by_key(key)
        wobj = shobj.worksheet(sheet)
    except gspread.SpreadsheetNotFound:
        return
    except gspread.WorksheetNotFound:
        return

    prot = obtain_prot(wobj)
    if not prot[0].startswith("#RelBot"): return
    if len(prot[1]) != 1: return
    print(prot)
    if len(prot[1][0]["editors"]["users"]) != 1 or (prot[1][0]["editors"]["users"][0] != "relbot@relbot-230215.iam.gserviceaccount.com"): return

    data = prot[0].split("|")
    server = data[1]
    name = data[2]

    if not server in charts.keys(): return
    if not name in charts[server]["charts"].keys(): return

    chart = copy.deepcopy(charts[server]["charts"][name])
    oldpeople = copy.deepcopy(chart["people"])
    chart["people"] = {}
    chart["keys"] = {}
    override = True
    try:
        keymark = wobj.findall("#RelKey")
    except gspread.CellNotFound:
        keymark = []
    k = 0
    keydata = []
    if len(keymark) != 2 and not override:
        await client.send_message(ctx.message.channel, "Invalid number of keymarkers found! You need two tiles named '#RelKey' on the upper-left and lower-right corners of your block of keys. The keys and relationships of this chart will be null.")
    else:
        if not override and (keymark[0].row +1 > keymark[1].row -1 or keymark[0].col+1 > keymark[1].col-1):
            await client.send_message(ctx.message.channel, "Invalid keymarker locations! They need to be in the upper-left and lower-right corners of your block of keys, at least one tile apart in both directions.\nThe keys and relationships of this chart will be null.")
        else:
            if override:
                 keydata = obtain_sheet_data(wobj, gspread.utils.rowcol_to_a1(wobj.row_count, 1), gspread.utils.rowcol_to_a1(wobj.row_count, wobj.col_count))
            else: keydata = obtain_sheet_data(wobj, gspread.utils.rowcol_to_a1(keymark[0].row+1, keymark[0].col+1), gspread.utils.rowcol_to_a1(keymark[1].row-1, keymark[1].col-1))
            k = 0
            for i, row in enumerate(keydata):
                for j, cell in enumerate(row['values']):
                    if not ('effectiveValue' in cell.keys() and 'effectiveFormat' in cell.keys()): continue
                    keyname = cell['effectiveValue']['stringValue']
                    color = cell['effectiveFormat']['backgroundColor']
                    if 'red' not in color.keys(): color['red'] = 0
                    if 'green' not in color.keys(): color['green'] = 0
                    if 'blue' not in color.keys(): color['blue'] = 0
                    keycolor = rgb_to_hex((color['red'], color['green'], color['blue']))
                    if keyname in chart["keys"].keys() or keycolor in chart["keys"].values():
                        continue
                    if keyname != "Haven't Met":
                        chart["keys"][keyname] = keycolor
                        k += 1


    try:
        datamark = wobj.findall("#RelData")
    except gspread.CellNotFound:
        datamark = []
    data = []
    if len(datamark) != 2 and not override:
        await client.send_message(ctx.message.channel, "Invalid number of data markers found! You need two tiles named '#RelData' on the upper-left and lower-right corners of your chart. The people and relationships of this chart will be null.")
    else:
        if not override and (datamark[0].row +1 >= datamark[1].row -1 or datamark[0].col+1 >= datamark[1].col-1):
            await client.send_message(ctx.message.channel, "Invalid data marker locations! They need to be in the upper-left and lower-right corners of your chart, at least one tile apart in both directions.\nThe people and relationships of this chart will be null.")
        else:
            if override:
                 data =  obtain_sheet_data(wobj, "A1", gspread.utils.rowcol_to_a1(wobj.row_count-2, wobj.col_count))
            else: data = obtain_sheet_data(wobj, gspread.utils.rowcol_to_a1(datamark[0].row, datamark[0].col), gspread.utils.rowcol_to_a1(datamark[1].row-1, datamark[1].col-1))
            k = 0
            names = []
            for i, cell in enumerate(data[0]['values'][1:]):
                if 'effectiveValue' in cell.keys():
                    person = cell['effectiveValue']['stringValue']
                    if person not in names:
                       chart["people"][person] = {
                                            "rels": {},
                                            "avatar": oldpeople[person]["avatar"] if person in oldpeople.keys() else None,
                                            "motto" : None
                       }
                       names.append(person)
                       k += 1
                    else:
                        names.append(None)
                else:
                    names.append(None)

    if keydata == [] or data == []:
        await client.send_message(ctx.message.channel, "Relationships skipped.")
    else:
        for i, row in enumerate(data[1:]):
            if 'effectiveValue' not in row['values'][0].keys():
                continue
            person = row['values'][0]['effectiveValue']['stringValue']
            if person not in names:
                continue
            for j, cell in enumerate(row['values'][1:]):
                if i == j:
                    if 'effectiveValue' in cell.keys():
                        chart["people"][person]["motto"] = cell['effectiveValue']['stringValue']
                    else: chart["people"][person]["motto"] = None
                else:
                    if not ('effectiveValue' in cell.keys() and 'effectiveFormat' in cell.keys()):
                        continue
                    if names[j] != None:
                        color = cell['effectiveFormat']['backgroundColor']
                        if 'red' not in color.keys(): color['red'] = 0
                        if 'green' not in color.keys(): color['green'] = 0
                        if 'blue' not in color.keys(): color['blue'] = 0
                        color = rgb_to_hex((color['red'], color['green'], color['blue']))
                        desc = cell['effectiveValue']['stringValue']
                        if desc == "Haven't Met": continue
                        if color not in chart["keys"].values():
                            continue

                        rel = list(chart["keys"].keys())[list(chart["keys"].values()).index(color)]
                        if desc.lower() == rel.lower(): desc = None
                        chart["people"][person]["rels"][names[j]] = {
                                                                "key": rel,
                                                                "desc": desc
                        }



    t = valid(chart, "chart")
    if isinstance(t, Exception):
            return
    else:
        charts[server]["charts"][name] = chart
        with open('charts.json', 'w') as file:    #save it
                json.dump(charts, file)
        if charts[server]["log"] != None:
            await client.send_message(client.get_channel(charts[server]["log"]), "Refreshed chart: " + name)


@client.command(pass_context = True)
async def retrieve(ctx, link = None, sheet = None, name = None):
    server = ctx.message.server.id
    global charts
    if link == None:
        await client.send_message(ctx.message.channel, "Please input the link to the Google Spreadsheets to retrieve from, followed by (optionally) the name to save the sheet as and the title of worksheet to pull from.")
        return
    link = str(link)
    if name != None: name = str(name)
    if sheet != None: sheet = str(sheet)
    try:
        gclient.login()
        shobj = gclient.open_by_url(link)
        if sheet != None: wobj = shobj.worksheet(sheet)
        else: wobj = shobj.sheet1
        if name == None: name = wobj.title
    except gspread.SpreadsheetNotFound:
        await client.send_message(ctx.message.channel, "Link failed! Please make sure you have a valid link to a Google Spreadsheet.")
        return
    except gspread.WorksheetNotFound:
        await client.send_message(ctx.message.channel, "Found no worksheet titled '" + sheet + "'!")
        return
    if name in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "There is already a chart titled '" + name + "'! Please pick a different title or !delete_chart.")
        return
    chart = {name: {
            'people' : {},
            'keys' : {},
            'owner' : ctx.message.author.id,
            'lock' : False,
            'auto' : False
            }
    }
    try:
        val = wobj.acell("A1").value
        override = True if val.startswith("#RelBot") else False
    except:
        override = False
    try:
        keymark = wobj.findall("#RelKey")
    except gspread.CellNotFound:
        keymark = []
    k = 0
    keydata = []
    print(override)
    if len(keymark) != 2 and not override:
        await client.send_message(ctx.message.channel, "Invalid number of keymarkers found! You need two tiles named '#RelKey' on the upper-left and lower-right corners of your block of keys. The keys and relationships of this chart will be null.")
    else:
        if not override and (keymark[0].row +1 > keymark[1].row -1 or keymark[0].col+1 > keymark[1].col-1):
            await client.send_message(ctx.message.channel, "Invalid keymarker locations! They need to be in the upper-left and lower-right corners of your block of keys, at least one tile apart in both directions.\nThe keys and relationships of this chart will be null.")
        else:
            if override:
                 keydata = obtain_sheet_data(wobj, gspread.utils.rowcol_to_a1(wobj.row_count, 1), gspread.utils.rowcol_to_a1(wobj.row_count, wobj.col_count))
            else: keydata = obtain_sheet_data(wobj, gspread.utils.rowcol_to_a1(keymark[0].row+1, keymark[0].col+1), gspread.utils.rowcol_to_a1(keymark[1].row-1, keymark[1].col-1))
            k = 0
            for i, row in enumerate(keydata):
                for j, cell in enumerate(row['values']):
                    if not ('effectiveValue' in cell.keys() or 'effectiveFormat' in cell.keys()): continue
                    keyname = cell['effectiveValue']['stringValue']
                    color = cell['effectiveFormat']['backgroundColor']
                    if 'red' not in color.keys(): color['red'] = 0
                    if 'green' not in color.keys(): color['green'] = 0
                    if 'blue' not in color.keys(): color['blue'] = 0
                    keycolor = rgb_to_hex((color['red'], color['green'], color['blue']))
                    if keyname in chart[name]["keys"].keys() or keycolor in chart[name]["keys"].values():
                        await client.send_message(ctx.message.channel, "Skipped key on tile " + gspread.utils.rowcol_to_a1(i+keymark[0].row+1, j+1+keymark[0].col) + ": a key with this name or color is already present!")
                        continue
                    if keyname != "Haven't Met":
                        chart[name]["keys"][keyname] = keycolor
                        k += 1

    await client.send_message(ctx.message.channel, str(k) + " keys located! Collecting people...")

    try:
        datamark = wobj.findall("#RelData")
    except gspread.CellNotFound:
        datamark = []
    data = []
    if len(datamark) != 2 and not override:
        await client.send_message(ctx.message.channel, "Invalid number of data markers found! You need two tiles named '#RelData' on the upper-left and lower-right corners of your chart. The people and relationships of this chart will be null.")
    else:
        if not override and (datamark[0].row +1 >= datamark[1].row -1 or datamark[0].col+1 >= datamark[1].col-1):
            await client.send_message(ctx.message.channel, "Invalid data marker locations! They need to be in the upper-left and lower-right corners of your chart, at least one tile apart in both directions.\nThe people and relationships of this chart will be null.")
        else:
            if override:
                 data =  obtain_sheet_data(wobj, "A1", gspread.utils.rowcol_to_a1(wobj.row_count-2, wobj.col_count))
            else: data = obtain_sheet_data(wobj, gspread.utils.rowcol_to_a1(datamark[0].row, datamark[0].col), gspread.utils.rowcol_to_a1(datamark[1].row-1, datamark[1].col-1))
            k = 0
            names = []
            for i, cell in enumerate(data[0]['values'][1:]):
                if 'effectiveValue' in cell.keys():
                    person = cell['effectiveValue']['stringValue']
                    if person not in names:
                       chart[name]["people"][person] = {
                                            "rels": {},
                                            "avatar": None,
                                            "motto" : None
                       }
                       names.append(person)
                       k += 1
                    else:
                        await client.send_message(ctx.message.channel, "Skipped coulumn " + str(i+1+datamark[0].col) + ": name is already present!")
                        names.append(None)
                else:
                    await client.send_message(ctx.message.channel, "Skipped coulumn " + str(i+1+datamark[0].col) + ": name is null!")
                    names.append(None)

    await client.send_message(ctx.message.channel, str(k) + " names located! Collecting relationships...")

    if keydata == [] or data == []:
        await client.send_message(ctx.message.channel, "Relationships skipped.")
    else:
        for i, row in enumerate(data[1:]):
            if 'effectiveValue' not in row['values'][0].keys():
                await client.send_message(ctx.message.channel, "Skipped row " + str(i+1++datamark[0].row) + ": name is null!")
                continue
            person = row['values'][0]['effectiveValue']['stringValue']
            if person not in names:
                await client.send_message(ctx.message.channel, "Skipped row " + str(i+1++datamark[0].row) + ": invalid name!")
                continue
            for j, cell in enumerate(row['values'][1:]):
                if i == j:
                    if 'effectiveValue' in cell.keys():
                        chart[name]["people"][person]["motto"] = cell['effectiveValue']['stringValue']
                    else: chart[name]["people"][person]["motto"] = None
                else:
                    if not ('effectiveValue' in cell.keys() or 'effectiveFormat' in cell.keys()):
                        await client.send_message(ctx.message.channel, "Skipped cell " + gspread.utils.rowcol_to_a1(datamark[0].row+i+1, datamark[0].col+j+1) + ": invalid contents!")
                        continue
                    if names[j] != None:
                        color = cell['effectiveFormat']['backgroundColor']
                        if 'red' not in color.keys(): color['red'] = 0
                        if 'green' not in color.keys(): color['green'] = 0
                        if 'blue' not in color.keys(): color['blue'] = 0
                        color = rgb_to_hex((color['red'], color['green'], color['blue']))
                        desc = cell['effectiveValue']['stringValue']
                        if desc == "Haven't Met": continue
                        if color not in chart[name]["keys"].values():
                            await client.send_message(ctx.message.channel, "Skipped cell " + gspread.utils.rowcol_to_a1(datamark[0].row+i+1, datamark[0].col+j+1) + ": invalid key!")
                            continue

                        rel = list(chart[name]["keys"].keys())[list(chart[name]["keys"].values()).index(color)]
                        if desc.lower() == rel.lower(): desc = None
                        chart[name]["people"][person]["rels"][names[j]] = {
                                                                "key": rel,
                                                                "desc": desc
                        }

    await client.send_message(ctx.message.channel, "Chart assembled! Validating...")
    t = valid(chart[name], "chart")
    if isinstance(t, Exception):
            out = io.BytesIO(str(t).encode('utf-8'))
            out.seek(0)
            await client.send_file(ctx.message.channel, out, filename = "error_log.txt", content = "Chart validation failed! Here are the error logs:")
            out.close()
            return
    else:
        await client.send_message(ctx.message.channel, "Pruned " + str(t) + " invalid entires...")
        charts[server]["charts"][name] = chart[name]
        await client.send_message(ctx.message.channel, "Chart retrieved!")
        with open('charts.json', 'w') as file:    #save it
                json.dump(charts, file)

embedict = {
    None: ("Basics:", "RelBot is a bot created to automatically support shipping/relationship/meme charting needs in any environment!\nInteraction with the bot is performed through commands; for ease of display those commands have been divided into categories.\nRun `!help <category>` with a name from the list below to read more, or `!help <command name>` receive information on specific commands!\nCommand categories:",
            ("Charting", "Commands devoted to basic creation and editing of charts"),
            ("Imaging", "Commands devoted to displaying created charts in image form"),
            ("Publishing", "Commands devoted to posting created charts as Google Spreadsheets, and retrieving them in reverse"),
            ("Security", "Commands devoted to ensuring chart safety, should one need it"),
            ("Utility", "Miscellaneous helper commands")
    ),
    'charting': ("Charting commands:", "This block of commands supports core operations with the chart system, such as creating/removing whole charts, people and relationship keys, and editing relationships within these charts.\nEach chart consists of a set of relationship keys and a set of person entries - each of which consists of a list of relationships with other people and, optionally, a motto and/or an avatar.\nRun `!help <command>` with the commands below for more info!",
            ("Chart manipulation:", "`!create_chart`, `!delete_chart`, `!reset`, `!rename`"),
            ("People manipulation:", "`!add_person`, `!add_people`, `!delete_person`, `!delete_people`, `!edit_motto`"),
            ("Relationship manipulation:", "`!add_key`, `!delete_key`, `!edit_rel`")
    ),
    'imaging' : ("Imaging commands:", "This block of commands handles printing out a created chart (or a selected relationship from one) in image form, as well as granting avatars to people within a chart.\nRun `!help <command>` with the commands below for more info!",
            ("Avatar handling:", "`!get_avatar`, `!set_avatar`"),
            ("Imaging proper:", "`!image`, `!image_rel`")
    ),
    'publishing' : ("Publishing commands:", "This block of commands handles publishing created charts as Google Spreadsheets, or retrieving them from ones, as well as automatic publishing.\nEvery server is granted a spreadhseet when a chart is first published; the charts are published as worksheets within it. \n`Warning:` if there are no published charts remaining, the spreadsheet is deleted whole! Keep this in mind, as links to the spreadsheet may no longer work if this happens.\nRun `!help <command>` with the commands below for more info!",
            ("Commands:", "`!publish`, `!unpublish`, `!unpublish_all`, `!view_published`, `!retrieve`"),
            ("See also:", "`!help extension`")
    ),
    'security' : ("!lock [chart name] {'true'/'false'}:", "This command allows to check the lock of a given chart, or change the state of the lock if you are the chart's creator or the server owner.\nWhen invoked with only the chart name, this command will return a message declaring whether the chart is locked or not, and by whom if it is;\nWhen invoked with the optional argument in addition, the bot checks whether the user is the server owner or the chart owner; if they are, the lock is set to the state specified.\nA locked chart may only be edited by either the chart owner or the server owner; commands overriden by that setting are marked as (lockable) in the `!help` documentation.",
            ("Use examples:", "`!lock my_chart`\n`!lock my_chart true`")
    ),
    'utility' : ("Utility functions:", "These are random minor functions for various helper tasks.\nRun `!help <command>` with the commands below for more info!",
            ("Commands:", "`!view`, `!assign`, `!resheet`, `!summon`, `!exile`, `!send_json`, `!send_backup_json`, `!validate_chart`, `!refresh`")
    ),
    'reset': ("!reset (server owner only)", "This command fully wipes all charts from this server's databank.\n`Warning:` The action is irreversible! You will be asked to confirm the decision by pressing a reaction to a prompt.",
            ("Use example:", "`!reset`")
    ),
    'use_backup': ("!use_backup ['chart'/'server'] {chart name} <json attachment>", "This command attempts to read the attached file and parse it into memory as a single chart under the specified name or as the whole content of the server, depending on the first argument.\nThe file will be validated to ensure it is a valid entry; should validation fail, error logs will be sent in return.\nThe 'server' mode is restricted to server owners only. `Warning`: the action will irreversibly replace the data linked to the server; you will be asked to confirm your decision by pressing a reaction on a prompt.",
            ("Use example:", "`!use_backup chart my_chart` <json attachment>\n`!use_backup server` <json attachment>")
    ),
    'exile' : ("!exile (server owner only)", "This command will signal the bot to leave the server. `Warning`: all data linked to the server will be deleted; you will be asked to confirm your decision by pressing a reaction on a prompt.",
            ("Use example:", "`!exile`")
    ),
    'edit_motto' : ("!edit_motto [chart name] [person name] {motto} (lockable)", "This command will edit the given person's motto - update it if one is given, or delete it if not.\nA `motto` can be a phrase or a word to be used as a description of the person, or a quote they would describe themselves as.\nMostly used in spreadsheet form.",
            ("Use example:", "`!edit_motto my_chart \"A Person\"`\n`!edit_motto my_chart \"A Person\" \"This is an example of a motto.\"`")
    ),
    'edit_rel' : ("!edit_rel [chart name] [source name] [target name] {key} {description} (lockable)", "This command will edit the specified chart to change a relationship from the source to the target.\nBoth people and the key (if given) must be present in the specified chart; the relationship will be deleted if no key is given, or change to match the arguments provided.\nKeep in mind all relationships are one-sided - there will be no change to the target's entry; you will have to enter these changes yourself in a separate command.",
            ("Use example:", "`!edit_rel my_chart \"Person A\" \"Person B\" Like`\n`!edit_rel my_chart Everyone Lance Loathe \"Hate that guy\"`\n`!edit_rel my_chart Someone \"Someone else\"`")
    ),
    'view_published' : ("!view_published", "This command will return the list of currently published charts, if there are any.",
            ("Use example:", "!view_published")
    ),
    'publish' : ("!publish [chart name] (lockable)", "This command will publish the chart specified.\n'Publishing' a chart means exporting it to the Google Spreadsheets into readable table form; the chart will be present on the server spreadsheet in the worksheet titled after the chart's name. If the server spreadsheet has not been created yet, it will be as part of the command.\nThe action is one-way and performed once only; no changes to the spreadsheet will affect the chart, and further changes to the chart will not be displayed in spreadsheet form - see `!retrieve` and `!autopublish` respectively for these features.",
            ("Use example:", "!publish my_chart"),
            ("See also:", "`!help extension`")
    ),
    'resheet' : ("!resheet [link]", "Should you think that the bot has lost the link to the server's spreadsheet, (or if you wish to attach your own) you can use this command to reestablish connection.\nThe spreadsheet you link to must be named after the server; if it is valid, all further operations will be performed with the spreadsheet provided.",
            ("Use example:", "`!resheet https://docs.google.com/spreadsheets/d/some_long_key`")
    ),
    'image_rel' : ("!image_rel [chart name] [person name] [person name]", "This command will return an image representing the relationship between two given people in a given chart, or a message warning that there is none.\nBoth people must be present within the given chart, and at least one must have a relationship to another for the image to be displayed; should that requirement be satisfied, the relationships will be displayed as arrows of the color specified by their keys, and supplied by the key names and the descriptions of the relationships, if they are present.",
            ("Use example:", "`!image_rel my_chart Six Seven`")
    ),
    'delete_key' : ("!delete_key [chart name] [key name] (lockable)", "This command will remove the specified key from the given chart.\n`Warning:`All relationships marked by that key will be terminated alongside the key; exercise caution when invoking this command, as this action is irreversible.",
            ("Use example:", "`!delete_key \"The World\" Love`")
    ),
    'retrieve' : ("!retrieve [link] {worksheet title} {chart name}", "This command will attempt to parse a chart from a Google Spreadsheet and save it as a chart under the given name. If no worksheet title is given, the bot will parse the first sheet; if no chart name is given, it will default to the sheet's title.\nThe sheet must contain two pairs of guiding markers: tiles marked with '#RelKey' and '#RelData' encompassing the keys and the chart proper, respectively. The key markers must be placed in the upper-left and lower-right corners of the key block, such that all keys must fit in the space strictly between the two; the data markers must be placed likewise, with the upper-left one on the crossing of the named row and column; names are expected to fill the top row and the leftmost column.\nShould either pair of markers fail, the relevant data will be skipped; this means that if either fail, there will be no relationships entered into the chart.\nPeople are parsed from the top row of the chart, and null/duplicate tiles are skipped; relationships are read as 'from the person to the left to the person above' with the keys determined by colour and descriptions determined by content of the tile, and rows marked by invalid names in the leftmost column are skipped; invalid tiles are also skipped.\nKeep in mind that \"Haven't Met\" is reserved as a value denoting no relationship, and as such will not be considered a valid key name.\nMottos are determined by the contents of the tiles from the row and column devoted to the same person.",
            ("Use example:", "`!retrieve https://docs.google.com/spreadsheets/d/some_long_key \"Some Sheet Title\" my_chart`"),
            ("See also:", "`!help extension`")
    ),
    'create_chart': ("!create_chart [chart name] <optional json attachment>", "This command will create a chart under the specified name.\nIf no file is attached, the chart created will be blank; otherwise the bot will attempt to validate the given file as a proper chart and, if successful, add it to memory under the specified name.\n`Warning:` It is highly encouraged to only use chart files created by this bot; while manual editing is possible, doing so may cause Lance to spontaneously combust.",
            ("Use example:", "`!create_chart \"My First Chart\"`")
    ),
    'delete_chart': ("!delete_chart [chart name] (lockable)","This command will permanently remove the given chart from the bot's memory.\n`Warning:` Exercise caution when invoking this command; the action is irreversible.",
            ("Use example:",  "`!delete_chart \"My First Chart\"`")
    ),
    'delete_person' : ("!delete_person [chart name] [person name] (lockable)", "This command will permanently remove the given person from the given chart.\n`Warning:` Exercise caution when invoking this command; the action is irreversible, and all relationships to this person will be terminated upon running this command.",
            ("Use example:", "`!delete_person my_chart \"The Grinch\"`")
    ),
    'get_avatar' : ("!get_avatar [chart name] [person name]", "This command will return the given person's avatar, or a warning message if there is none.\n`Warning:` Avatars are stored locally and separately; if the chart specifies there is one, but no matching image can be found (for instance, if the chart had been imported via json), the entry for that avatar well be annulled.",
            ("Use example:", "`!get_avatar my_chart Person`")
    ),
    'assign' : ("!assign (server owner only)", "This command will assign a channel this command is posted in as the channel for the bot's logs.\nShould any error arise during a command's execution, the failure messages will be mailed there.",
            ("Use example:", "`!assign`")
    ),
    'add_key' : ("!add_key [chart name] [key name] [key colour] (lockable)", "This command will add a relationship key to the specified chart.\nRelationship keys define what relationships are possible between people in a chart. They are specified by a name and a colour, each of which must be unique.\nThe colors are to be entered as a hexidecimal RGB code with or without the # symbol in front.",
            ("Use example:", "`!add_key my_chart my_key #ffffff`\n`!add_key my_chart my_key ff0000`")
    ),
    'view' : ("!view {chart name} {person name}", "This command allows to traverse the server's charts in a readable manner, depending on the arguments passed.\nIf no arguments are supplied, the command will return a list of charts present on the server, or a warning message if there are none.\nIf a chart name is supplied, the command will return information about its contents - username of the owner, lock state, autopublishing state and the list of key and person entries, if they are present.\nIf both a chart name and a person name are supplied, the command will return information about the person's entry within the chart (if it exists) - the motto and list of relationships with other people (with descriptions, if they are present).\nIf at any point the length of the returned message exceeds a thousand characters, it is returned as a text file instead.",
            ("Use example:", "`!view`\n`!view my_chart`\n`!view my_chart Person`")
    ),
    'summon' : ("!summon", "This command will make the bot send a private message with the OAuth2 link required to invite it to another server. Keep in mind you will need server owner priveleges to be able to invite it!",
            ("Use example:", "`!summon`")
    ),
    'autopublish' : ("!autopublish [chart name] {'true'/'false'} (lockable)", "This command allows to check whether the specified chart is set to be autopublished, or to turn the autopublishing of that chart on/off.\nWith this setting on, the chart will be quietly uploaded to the server's spreadsheet every hour; be aware that it requires the server spreadsheet to exist, and as such at least one chart must already be published for this server.",
            ("Use example:", "`!autopublish my_chart`\n`!autopublish my_chart true`"),
            ("See also:", "`!help extension`")
    ),
    'delete_people' : ("!delete_people [chart name] {any number of people names} (lockable)", "This command removes all valid person entries from the specified chart, along with any and all relationships linked to them.\nThe bot will warn you about every invalid name passed and skip them; the command is otherwise identical to `!delete_person`.\n`Warning:` This action is irreversible and will remove all relationships citing the deleted people as targets.",
            ("Use example:", "`!delete_people \"This Room\" Albert Bill Candy Dave Myself`")
    ),
    'add_people' : ("!add_people [chart name] {any number of people names} (lockable)", "This command adds all valid person entries given to the specified chart.\nThe bot will warn you about any names already present in the chart and skip them; the command is otherwise identical to `!add_person`.\nKeep in mind entries added are blank; you will need to add details to them yourself through use of other commands.",
            ("Use example:", "`!add_people \"My Yard\" Boi1 Boi2 Boi3 Boi4 Boi5`")
    ),
    'unpublish_all' : ("!unpublish_all (server owner only)", "This command deletes the entire server's Google Spreadsheet along with any and all published charts.\n`Warning:` The action, while reversible through repeted use of the `!publish` command, will invalidate the previous spreadsheet links, as a new spreadsheet will have to be generated for charts to be published. You will be asked to confirm your decision by pressing a reaction to a prompt.",
            ("Use example:", "`!unpublish_all`")
    ),
    'add_person' : ("!add_person [chart name] [person name] (lockable)", "This command adds a person entry under the given name to the specified chart.\nThe name must not be in use for the command to work; keep in mind the added entry will be blank.",
            ("Use example:" "`!add_person my_chart Person`")
    ),
    'unpublish' : ("!unpublish [chart name] (lockable)", "This command removes a chart from the server Google Spreadsheet.\n`Warning:` this action is partially irreversible if the command is applied to the last published chart; the whole spreadsheet will be deleted alongside, invalidating past spreadsheet links.",
            ("Use example:", "`!unpublish my_chart`")
    ),
    'validate_chart' : ("!validate_chart {chart name}", "Every chart is automatically validated before every major operation, such as parsing it into an image or spreadsheet. This command allows the user to manually validate a specified chart or the whole server databank, if no chart name is passed.\nValidation  is performed in two steps; firstly the bot ensures the chart's structure is intact and compliant with internal standarts; if it is not, the chart is rejected and an error log file is sent in return. \n Secondly, all references to nonexistent keys or people are removed; this is referenced as 'pruning'. Pruning does not affect the validity of the chart and serves as a way to discard garbage entries.\nIf a chart fails validation, please consider alerting Lance and recreating the chart anew; if the whole server fails validation, please knock on Lance's thick skull and tell him he probably has broken something again.",
            ("Use example:", "`!validate_chart`\n`!validate_chart my_chart`")
    ),
    'lock' : ("!lock [chart name] {'true'/'false'}:", "This command allows to check the lock of a given chart, or change the state of the lock if you are the chart's creator or the server owner.\nWhen invoked with only the chart name, this command will return a message declaring whether the chart is locked or not, and by whom if it is;\nWhen invoked with the optional argument in addition, the bot checks whether the user is the server owner or the chart owner; if they are, the lock is set to the state specified.\nA locked chart may only be edited by either the chart owner or the server owner; commands overriden by that setting are marked as (lockable) in the `!help` documentation.",
            ("Use examples:", "`!lock my_chart`\n`!lock my_chart true`")
    ),
    'set_avatar' : ("!set_avatar [chart name] [person name] <optional image attachment> (lockable)", "This command will edit the person's avatar entry, removing the avatar if no image is attached with the message, or attempting to download and save the avatar to attach it to the person specified.\nIf an image is attached, it must be a square `png` file; non-square images are rejected due to cropping ambiguity.\nIf the attached image is deemed suitably square, it will be resized to  size of 128x128 pixels and saved locally to be used in imaging operations such as `!image` and `!image_rel`.",
            ("Use example:", "`!set_avatar my_chart Person` <image attachment>")
    ),
    'image' : ("!image [chart name]", "This command will parse the specified chart into an image for the viewing pleasure of the user.\nEvery person entry within the chart will be pooled and displayed in the image; relationships between those people will be shown as arrows from the source to the target, coloured according to the key colours; the legend of the chart will be displayed to the left of it and will list all keys in use.\nThe bot will paste in avatars of the people in the chart if these avatars are present; if a person lacks an avatar, a placeholder is provided instead.",
            ("Use example:", "`!image my_chart`")
    ),
    'send_backup_json': ("!send_backup_json {chart name}", "This command will return the record for the specified chart (or the whole server, if no name is passed) in JSON format.\nAll of the bot's database is sent to the backup file every 15 minutes. Apart from using this backup file instead of the main storage, this command is nearly identical to `!send_json`; it can be used to undo a recent action, provided you are timely (and, possibly, lucky) enough.",
            ("Use examples:", "`!send_backup_json my_chart`\n`!send_backup_json`")
    ),
    'refresh' : ("!refresh", "For all bot functions within a server the bot's databank must have an entry for that server. Usually such an entry is created as soon as the bot joins the server; however, if you sense a catastrophic failure (usually displayed by the bot failing to respond to any and all commands), you may attempt to manually add such an entry using this command.\nIf the server is already logged within the databank, this command will raise a warning and do nothing else; otherwise it will create a blank entry for your server, allowing you to resume operations anew.",
            ("Use example:", "`!refresh`")
    ),
    'send_json' : ("!send_json {chart name}", "This command will return the entry for a specified chart (or the whole server, if no chart name is passed) in JSON format.\nThis can be used to transfer data between servers in conjunction with `!use_backup`; keep in mind that avatar files are not included (though their entries will remain valid).",
            ("Use examples:", "`!send_json my_chart`\n`!send_json`")
    ),
    'rename' : ("!rename ['chart'/'key'/'person'] [chart name] [target deadname/chart newname] {target name v2.0}", "This command will rename a given entry, be it a person, key, or the whole chart, depending on the mode specified.\nIf this is use to rename a chart, only two arguments need to follow - the old chart name, followed by the new one. Otherwise, three arguments are required - the target chart name, the old name of the target within it, and the new name to change it to.\nThe entry is renamed alongside all its mentions in the relationships - people that have a link to the renamed person will have that link retargeted, and all relationships that bear a renamed key will also be renamed.",
            ("Use examples:", "`!rename chart my_chart \"My Chart\"`\n`!rename key my_chart Love Hate`\n`!rename person my_chart Lance Lnace`")
    )

}

client.remove_command("help")
@client.command(pass_context = True)
async def help(ctx, value = None):
    global embedict
    if value != None:
        value = str(value).lower()
        if value.startswith("!"): value = value[1:]
    if value not in embedict.keys():
        await client.send_message(ctx.message.channel, "Invalid argument! No such command/help entry found.")
        return
    embed = discord.Embed(
                    title = embedict[value][0],
                    description = embedict[value][1],
                    colour = discord.Color.purple()
                )
    if len(embedict[value])>2:
        for i in range(2, len(embedict[value])):
            embed.add_field(name = embedict[value][i][0], value = embedict[value][i][1])
    embed.set_author(name = ctx.message.server.me.name, icon_url = ctx.message.server.me.avatar_url)
    if value == "extension":
        embed.set_footer(text = "Lance paid $5 for this, what a hecking idjit, pass it on")
    await client.send_message(ctx.message.channel, embed = embed)


@client.command(pass_context = True)
async def rename(ctx, mode = None, chart = None, arg1 = None, arg2 = None):
    if mode not in ('chart','person','key') or chart == None or arg1 == None:
        await client.send_message(ctx.message.channel, "Invalid arguments! Please input the mode ('chart', 'person' or 'key'), followed by the name of the chart (and the name of the entry in it, if you are not renaming the chart itself) and the name to replace it with.")
        return
    global charts
    server = ctx.message.server.id
    chart = str(chart)
    if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
    if mode == 'chart':
        if arg1 in charts[server]["charts"].keys():
            await client.send_message(ctx.message.channel, "A chart with this name already exists! Please consider choosing something else.")
            return
        charts[server]["charts"][arg1] = copy.deepcopy(charts[server]["charts"][chart])
        del charts[server]["charts"][chart]
        gclient.login()
        try:
            shobj = gclient.open_by_url(charts[server]["sheet"])
            wobj = shobj.worksheet(chart)
            shobj.duplicate_sheet(wobj.id, new_sheet_name = arg1)
            shobj.del_worksheet(wobj)
        except Exception as e:
            print(e)

        for name, person in charts[server]["charts"][arg1]["people"].items():
            if person["avatar"] != None:
                newname = server+"_"+arg1+"_"+name+".png"
                with open(person["avatar"], "r") as source:
                    with open(newname, "w") as dest:
                        shutil.copyfileobj(source, dest)
                person["avatar"] = newname
        await client.send_message(ctx.message.channel, "Chart renamed!")
    else:
        if arg2 == None:
            await client.send_message(ctx.message.channel, "Invalid arguments! Please input the mode ('chart', 'person' or 'key'), followed by the name of the chart (and the name of the entry in it, if you are not renaming the chart itself) and the name to replace it with.")
            return
        if mode == 'key':
            if arg1 not in charts[server]["charts"][chart]["keys"].keys():
                await client.send_message(ctx.message.channel, "No such key found!")
                return
            if arg2 in charts[server]["charts"][chart]["keys"].keys():
                await client.send_message(ctx.message.channel, "A key with this name already exists! Please consider something else.")
                return
            charts[server]["charts"][chart]["keys"][arg2] = copy.deepcopy(charts[server]["charts"][chart]["keys"][arg1])
            del charts[server]["charts"][chart]["keys"][arg1]
            for person in charts[server]["charts"][chart]["people"].values():
                for rel in person["rels"].values():
                    if rel["key"] == arg1: rel["key"] = arg2
            await client.send_message(ctx.message.channel, "Key renamed!")
        elif mode == 'person':
            if arg1 not in charts[server]["charts"][chart]["people"].keys():
                await client.send_message(ctx.message.channel, "No such person found!")
                return
            if arg2 in charts[server]["charts"][chart]["people"].keys():
                await client.send_message(ctx.message.channel, "A person with this name already exists! Please consider something else.")
                return
            charts[server]["charts"][chart]["people"][arg2] = copy.deepcopy(charts[server]["charts"][chart]["people"][arg1])
            del charts[server]["charts"][chart]["people"][arg1]
            for person in charts[server]["charts"][chart]["people"].values():
                for name in person["rels"].keys():
                    if name == arg1:
                        person["rels"][arg2] = copy.deepcopy(person["rels"][arg1])
                        del person["rels"][arg1]
            await client.send_message(ctx.message.channel, "Person renamed!")
    with open('charts.json', 'w') as file:
        json.dump(charts, file)






@client.command(pass_context = True)
async def publish(ctx, name = None):
    server = ctx.message.server.id
    global charts
    if name == None:
        await client.send_message(ctx.message.channel, "Please input the name of the chart to publish.")
        return
    name = str(name)
    if not name in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
    if charts[server]["charts"][name]["lock"] and ctx.message.author.id not in (charts[server]["charts"][name]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][chart]["owner"])) + "!")
        return
    await client.send_message(ctx.message.channel, "Validating chart...")
    t = valid(charts[server]["charts"][name], "chart")
    if isinstance(t, Exception):
            out = io.BytesIO(str(t).encode('utf-8'))
            out.seek(0)
            await client.send_file(ctx.message.channel, out, filename = "error_log.txt", content = "Chart validation failed! Here are the error logs:")
            out.close()
            return
    else:
        await client.send_message(ctx.message.channel, "Pruned " + str(t) + " invalid entires...")
        people = len(charts[server]["charts"][name]["people"])
        keys = len(charts[server]["charts"][name]["keys"])
        sheets = charts[server]["sheet"]
        gclient.login()
        if sheets == None:
            await client.send_message(ctx.message.channel, "Creating server spreadsheet...")
            shobj = gclient.create(ctx.message.server.name)
            shobj.share(None, "anyone", "writer", with_link=True)
            charts[server]["sheet"] = "https://docs.google.com/spreadsheets/d/" + shobj.id
        else:
            shobj = gclient.open_by_url(charts[server]["sheet"])
            with open('charts.json', 'w') as file:    #save it
                json.dump(charts, file)
        try:
            wobj = shobj.worksheet(name)
            wobj.resize(rows = 1)
            wobj.resize(cols = 1)   #avoid problems with resize formatting the hard way
            wobj.resize(rows = people+3)
            wobj.resize(cols = max(people+1,keys+1))
        except gspread.exceptions.WorksheetNotFound:
            wobj = shobj.add_worksheet(name, people+3, max(people+1,keys+1))
        try:
            shobj.del_worksheet(shobj.worksheet("Sheet1"))
        except: pass
        wid = wobj.id

        ucreq = {"rows" : [], "fields":"*", "start" : {
                                            "sheetId":wid,
                                            "rowIndex":0,
                                            "columnIndex":0
                                            }
        }
        #first row - blank first cell, rest are names in bold
        firstrow = {"values" : []}
        basiccell = {"userEnteredValue":{"stringValue":""},"userEnteredFormat":{"backgroundColor":{"red":1,"blue":1,"green":1},"textFormat":{"foregroundColor":{"red":0,"blue":0,"green":0},"bold":True}} }
        blacktile = {"userEnteredValue":{"stringValue":""},"userEnteredFormat":{"backgroundColor":{"red":0,"blue":0,"green":0},"textFormat":{"foregroundColor":{"red":1,"blue":1,"green":1},"bold":True}} }
        startcell = {"userEnteredValue":{"stringValue":"#RelBot|"+server+"|"+name},"userEnteredFormat":{"backgroundColor":{"red":1,"blue":1,"green":1},"textFormat":{"foregroundColor":{"red":0,"blue":0,"green":0},"bold":True}} }
        firstrow["values"].append(startcell)
        bcellcopy = copy.deepcopy(basiccell)
        for k in sorted(charts[server]["charts"][name]["people"].keys()):
            bcellcopy["userEnteredValue"]["stringValue"] = k;
            firstrow["values"].append(copy.deepcopy(bcellcopy))
        ucreq["rows"].append(copy.deepcopy(firstrow))
        #next rows - start with name, fill out rels
        peps = sorted(list(charts[server]["charts"][name]["people"].keys()))
        for person, values in sorted(charts[server]["charts"][name]["people"].items()):
            personrow = {"values" : []}                           # [
            startcell = copy.deepcopy(basiccell)                  # [
            startcell["userEnteredValue"]["stringValue"] = person # [ places name
            personrow["values"].append(copy.deepcopy(startcell))  # [
            for pos in peps:
                #iterate over the list of people - if there is a rel for them, make it happen, else placeholder
                relcell = copy.deepcopy(basiccell)

                if pos in values["rels"].keys():    #there is a rel - grab the rel's color
                    colors = scale_rgb_tuple(hex_to_rgb(charts[server]["charts"][name]["keys"][values["rels"][pos]["key"]]))
                    relcell["userEnteredFormat"]["backgroundColor"]={
                                    "red": colors[0],         #
                                    "blue": colors[2],        #enter it in
                                    "green": colors[1]        #
                    }
                    lum = (colors[0]*0.299 + colors[1]*0.587 + colors[2]*0.114)
                    if lum > 0.5: lum = 0     #calculate luminocity and choose contrary text color
                    else: lum = 1
                    relcell["userEnteredFormat"]["textFormat"]["foregroundColor"]={
                                    "red": lum,
                                    "blue": lum,
                                    "green": lum
                    }
                    if values["rels"][pos]["desc"] != None:
                        relcell["userEnteredValue"]["stringValue"]=values["rels"][pos]["desc"]
                    else:
                        relcell["userEnteredValue"]["stringValue"]=values["rels"][pos]["key"].title()  #insert rel name
                elif pos == person:      #this is the relperson - insert blacktile with motto
                    btile =  copy.deepcopy(blacktile)
                    if values["motto"]!=None:
                        btile["userEnteredValue"]["stringValue"]=values["motto"]
                    relcell = copy.deepcopy(btile)
                else:                      #this is no rel - insert placeholder
                    relcell["userEnteredFormat"]["backgroundColor"]={
                                    "red": 0.8,
                                    "blue": 0.8,
                                    "green": 0.8
                    }
                    relcell["userEnteredValue"]["stringValue"]="Haven't Met"
                personrow["values"].append(relcell)
            ucreq["rows"].append(copy.deepcopy(personrow))
        #rel rows placed, place border
        personrow = {"values" : []}
        for i in range(max(people+1, keys+1)):
            personrow["values"].append(blacktile)
        ucreq["rows"].append(copy.deepcopy(personrow))
        #border placed, place key row
        personrow = {"values" : []}
        personrow["values"].append(basiccell)
        personrow["values"][0]["userEnteredValue"]["stringValue"]="Chart keys:"
        for key, color in charts[server]["charts"][name]["keys"].items():
            colorcell = copy.deepcopy(basiccell)
            colors = scale_rgb_tuple(hex_to_rgb(color)) #acquire key color
            colorcell["userEnteredFormat"]["backgroundColor"]={
                            "red": colors[0],         #
                            "blue": colors[2],        #enter it in
                            "green": colors[1]        #
            }
            lum = (colors[0]*0.299 + colors[1]*0.587 + colors[2]*0.114)
            if lum > 0.5: lum = 0     #calculate luminocity and choose contrary text color
            else: lum = 1
            colorcell["userEnteredFormat"]["textFormat"]["foregroundColor"]={
                            "red": lum,
                            "blue": lum,
                            "green": lum
            }
            colorcell["userEnteredValue"]["stringValue"]=key  #insert key name
            personrow["values"].append(copy.deepcopy(colorcell))
        ucreq["rows"].append(copy.deepcopy(personrow))
        request = {"requests":[{"updateCells": ucreq}]}
        #all rows placed - request formed
        protreq = {"range":{
                        "sheetId" : wid,
                        "startRowIndex" : 0,
                        "startColumnIndex" : 0,
                        "endRowIndex" : 1,
                        "endColumnIndex" : 1
        }, "warningOnly" : False,
           "editors" : {
                        "users" : ["relbot@relbot-230215.iam.gserviceaccount.com"]
        }
        }
        try:
            prot = obtain_prot(wobj)
        except:
            request = {"requests":[{"updateCells": ucreq},{"addProtectedRange": {"protectedRange": protreq}}]};

        #...and we send it as a batch, cause I ain't rewriting the shit above to make it adhere to update_cells
        shobj.batch_update(request)
        await client.send_message(ctx.message.channel, "Chart published! You may find this server's charts on:\n"+charts[server]["sheet"])




@client.command(pass_context = True)
async def unpublish(ctx, name = None):
    server = ctx.message.server.id
    global charts
    if name == None:
        await client.send_message(ctx.message.channel, "Please input the name of the chart to unpublish!")
        return
    name = str(name)
    me = ctx.message.server.me
    if not name in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
    if charts[server]["charts"][name]["lock"] and ctx.message.author.id not in (charts[server]["charts"][name]["owner"], ctx.message.server.owner.id):
        await client.send_message(ctx.message.channel, "This chart is locked by " + str(ctx.message.server.get_member(charts[server]["charts"][name]["owner"])) + "!")
        return
    if charts[server]["sheet"] == None:
        await client.send_message(ctx.message.channel, "This server has not published any chart!")
        return
    gclient.login()
    shobj = gclient.open_by_url(charts[server]["sheet"])
    try:
        wobj = shobj.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        await client.send_message(ctx.message.channel, "No published chart with this name found!")
        return
    if len(shobj.worksheets()) == 1:
        msg = await client.send_message(ctx.message.channel, "This will remove the final chart from the Google Spreadsheets, deleting the server spreadsheet. Are you sure?")
        await client.add_reaction(msg, '✅')
        await client.add_reaction(msg, '❌')
        res = await client.wait_for_reaction(['✅','❌'], message=msg, timeout=30, user=ctx.message.author)
        if res == None:
            await client.remove_reaction(msg, '✅', me)
            await client.remove_reaction(msg, '❌', me)
            await client.add_reaction(msg, "⏰")
        if res.reaction.emoji == '❌':
            await client.remove_reaction(msg, '✅', me)
            await client.remove_reaction(msg, '❌', me)
        if res.reaction.emoji == '✅':
            await client.remove_reaction(msg, '✅', me)
            await client.remove_reaction(msg, '❌', me)
            gclient.del_spreadsheet(shobj.id)
            await client.send_message(ctx.message.channel, "All published charts removed; spreadsheet deleted.")
            charts[server]["sheet"] = None
            with open('charts.json', 'w') as file:    #save it
                json.dump(charts, file)
    else:
        shobj.del_worksheet(wobj)
        await client.send_message(ctx.message.channel, "Published chart deleted!")


@client.command(pass_context = True)
async def resheet(ctx, link = None):
    server = ctx.message.server.id
    global charts
    if link == None:
        await client.send_message(ctx.message.channel, "Please input the link to reattach to!")
        return
    link = str(link)
    try:
        gclient.login()
        if ctx.message.server.name == gclient.open_by_url(link).title:
            await client.send_message(ctx.message.channel, "Link restored!")
            charts[server]["sheet"] = link
            with open('charts.json', 'w') as file:    #save it
                json.dump(charts, file)
        else:
            raise Exception
    except:
        await client.send_message(ctx.message.channel, "Sorry, this does not seem to be the link.")

@client.command(pass_context = True)
async def unpublish_all(ctx):
    server = ctx.message.server.id
    global charts
    me = ctx.message.server.me
    if charts[server]["sheet"] == None:
        await client.send_message(ctx.message.channel, "This server has not published any chart!")
        return
    if ctx.message.author != ctx.message.server.owner: #respond to server owners only
        return
    msg = await client.send_message(ctx.message.channel, "This will remove all charts from the Google Spreadsheets. Are you sure?")
    await client.add_reaction(msg, '✅')
    await client.add_reaction(msg, '❌')
    res = await client.wait_for_reaction(['✅','❌'], message=msg, timeout=30, user=ctx.message.author)
    if res == None:
        await client.remove_reaction(msg, '✅', me)
        await client.remove_reaction(msg, '❌', me)
        await client.add_reaction(msg, "⏰")
    if res.reaction.emoji == '❌':
        await client.remove_reaction(msg, '✅', me)
        await client.remove_reaction(msg, '❌', me)
    if res.reaction.emoji == '✅':
        await client.remove_reaction(msg, '✅', me)
        await client.remove_reaction(msg, '❌', me)
        gclient.login()
        shobj = gclient.open_by_url(charts[server]["sheet"])
        gclient.del_spreadsheet(shobj.id)
        await client.send_message(ctx.message.channel, "All published charts removed; spreadsheet deleted.")
        charts[server]["sheet"] = None
        with open('charts.json', 'w') as file:    #save it
            json.dump(charts, file)

@client.command(pass_context = True)
async def killjoy(ctx):
    if ctx.message.author.id == "190524109937967105": sys.exit()





serschem = {"definitions" : {
        "keys" : {
                "type" : "object",
                "additionalProperties" : {
                    "type" : "string",
                    "pattern" : "[a-f\d]{6}"
                }
        },
        "person" : {
                "type" : "object",
                "properties" : {
                    "rels" : {
                        "type" : "object",
                        "additionalProperties" : {
                            "type" : "object",
                            "properties":{
                                "desc" : {"type" : ["string", "null"]},
                                "key" : {"type" : "string"}
                            },
                            "required":["desc", "key"]
                        },

                    },
                    "avatar" : {"type" : ["string", "null"]},
                    "motto" : {"type" : ["string", "null"]}
                },
                "required" : ["rels", "avatar", "motto"]
        },
        "people" : {
                "type" : "object",
                "additionalProperties" : {"$ref" : "#/definitions/person"}
        },
        "charts": {
                "type" : "object",
                "properties" : {
                    "people" : {"$ref" : "#/definitions/people"},
                    "keys" : {"$ref": "#/definitions/keys"},
                    "owner" : {"type" : "string"},
                    "lock" : {"type" : "boolean"},
                    "auto" : {"type" : "boolean"}
                },
                "required" : ["people", "keys", "owner", "lock", "boolean"]
        },
    },
    "type" : "object",
    "propertyNames" : "[\d]",
     "properties" : {
                "charts" : {
                    "type" : "object",
                    "additionalProperties" : {"$ref": "#/definitions/charts"}
                },
                "log" : {
                    "type" :  ["string", "null"],
                    "pattern" : "([\d]|null)"
                    },
                "sheet":{
                    "type" : ["string", "null"]
                }
                },
     "required" : ["charts","log"]
}

chaschem = {"definitions" : {
        "keys" : {
                "type" : "object",
                "additionalProperties" : {
                    "type" : "string",
                    "pattern" : "[a-f\d]{6}"
                }
                },
        "person" : {
                "type" : "object",
                "properties" : {
                    "rels" : {
                        "type" : "object",
                        "additionalProperties" : {
                            "type" : "object",
                            "properties":{
                                "desc" : {"type" : ["string", "null"]},
                                "key" : {"type" : "string"}
                            },
                            "required":["desc", "key"]
                        },
                    "avatar" : {"type" : ["string", "null"]},
                    "motto" : {"type" : ["string", "null"]}
                    },
                },
                "required" : ["rels", "avatar", "motto"]
        },
        "people" : {
                "type" : "object",
                "additionalProperties" : {"$ref" : "#/definitions/person"}
        }
    },
    "type" : "object",
    "properties" : {
        "people" : {"$ref" : "#/definitions/people"},
        "keys" : {"$ref": "#/definitions/keys"},
        "owner" : {"type" : "string"},
        "lock" : {"lock" : "boolean"},
        "auto" : {"type": "boolean"}
        },
        "required" : ["people", "keys", "owner", "lock", "auto"]
}

def valid(stuff, kind):
    global chaschem
    global serschem
    if kind == "server":
        sch = serschem
    elif kind == "chart":
        sch = chaschem
    else: return None
    try:
        validate(stuff, sch)
        return prune(stuff, kind)
    except Exception as e:
        return e

def prune(stuff, kind):
    n = 0;
    if kind == "chart":
        keys = stuff["keys"].keys()
        people = stuff["people"].keys()
        for person, data in stuff["people"].items():
            for relname, relkey in data["rels"].items():
                if not (relname in people or relkey["key"] in keys):
                    del data[relname]
                    n+=1
        return n
    elif kind == "server":
        for index, chart in stuff["charts"].items():
            n += prune(chart, "chart")
        return n

def rgb_to_hex(rgb):
    """Convert an rgb 3-tuple to a hexadecimal color string.

    Example:
    >>> print(rgb_to_hex((0.50,0.2,0.8)))
    #8033cc
    """
    return '%02x%02x%02x' % tuple([round(x*255) for x in rgb])

def hex_to_rgb(hex_str):
    """Returns a tuple representing the given hex string as RGB.

    >>> hex_to_rgb('CC0000')
    (204, 0, 0)
    """
    if hex_str.startswith('#'):
        hex_str = hex_str[1:]
    return tuple([int(hex_str[i:i + 2], 16) for i in range(0, len(hex_str), 2)])

def scale_rgb_tuple(rgb, down=True):
    """Scales an RGB tuple up or down to/from values between 0 and 1.

    >>> scale_rgb_tuple((204, 0, 0))
    (.80, 0, 0)
    >>> scale_rgb_tuple((.80, 0, 0), False)
    (204, 0, 0)
    """
    if not down:
        return tuple([int(c*255) for c in rgb])
    return tuple([round(float(c)/255, 2) for c in rgb])


@client.command(pass_context = True)
async def image(ctx, chart = None):
    server = ctx.message.server.id
    global charts
    if chart == None:
        await client.send_message(ctx.message.channel, "Invalid arguments! Please input the name of the chart to parse.")
        return
    if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
    await client.send_message(ctx.message.channel, "Validating chart...")
    t = valid(charts[server]["charts"][chart], "chart")
    if isinstance(t, Exception):
            out = io.BytesIO(str(t).encode('utf-8'))
            out.seek(0)
            await client.send_file(ctx.message.channel, out, filename = "error_log.txt", content = "Chart validation failed! Here are the error logs:")
            out.close()
            return
    else:
        await client.send_message(ctx.message.channel, "Pruned " + str(t) + " invalid entires...")
        task = partial(build_graph, server, chart)
        img = await client.loop.run_in_executor(None, task)
        bimg = io.BytesIO()
        img.save(bimg, "PNG")
        bimg.seek(0)
        await client.send_file(ctx.message.channel, bimg, filename = chart+".png", content = "Chart "+chart+" in image form:")
        bimg.close()




def build_graph(server, chart):
    global charts
    n = len(charts[server]["charts"][chart]["people"])      #number of people
    tA = 360/n; bA = (180 - n)/2; oA = tA/8                           #angles for calculations
    if n == 1: Rg = 0                                      #edge case
    elif n == 2:
        Rg = 120
        oA = 5                                   #edge case
    else: Rg = 2*90*(math.sin(math.radians(bA)))/(math.sin(math.radians(tA)))  #main case
#    k = len(charts[server]["charts"][name]["keys"])        #number of keys
    l = math.ceil((Rg + 90)*2/24)*24+24 #vertical and initial horizontal size of the whole image
    sk = int(l/24)                        #number of keys we can fit in in one vertical row
#    nk = math.ceil(k/sk)             #number of key rows
    img = Image.new("RGB", (l, l), '#ffffff')
    draw = ImageDraw.Draw(img)
    center = (int(l/2), int(l/2))
    used_keys = set()
    outangle = 90                       #starting degree - down
#    ring = Image.open('ring.png', "RGB")
    place = Image.open('placeholder.png')
    mask = Image.open('mask.png')
    peps = sorted(list(charts[server]["charts"][chart]["people"].keys()))
    add = lambda xs,ys:(xs[0]+ys[0], xs[1]+ys[1]) #tuple summation
    sub = lambda xs,ys:(xs[0]-ys[0], xs[1]-ys[1]) #tuple subtraction
    for index, person in enumerate(peps):
        outangle = 90+tA*index
        Ro = 30 if n == 3 else 50
        out = add(center, (int(math.cos(math.radians(outangle+oA))*(Rg-Ro)), int(math.sin(math.radians(outangle+oA))*(Rg-Ro))))
        for innerind, pos in enumerate(peps):
            if pos in charts[server]["charts"][chart]["people"][person]["rels"].keys():
                inangle = 90+tA*innerind
                color = '#'+charts[server]["charts"][chart]["keys"][charts[server]["charts"][chart]["people"][person]["rels"][pos]["key"]]
                inp = add(center, (int(math.cos(math.radians(inangle-oA))*(Rg-Ro)), int(math.sin(math.radians(inangle-oA))*(Rg-Ro))))
                draw.line([out, inp], color, width = 2)
                mid = tuple(v/2 for v in add(out, inp))
                vector = tuple(v/15 for v in sub(out, inp))
                mid = sub(mid, vector)
                offset = (vector[1]/5, -vector[0]/5)
                draw.polygon([sub(mid, vector), add(mid, offset), sub(mid, offset)], color, color)                               #|
                #draw.line([add(mid, vector), add(mid, offset)], color, width = 2)  #|add arrowpoint
                #draw.line([add(mid, vector), sub(mid, offset)], color, width = 2)  #|
                used_keys.add(charts[server]["charts"][chart]["people"][person]["rels"][pos]["key"])
    #rel lines done, paste avatars
    coords = {}
    for index, person in enumerate(peps):
        outangle = 90+index*tA
        if index == 0: point = add(center, (0, math.ceil(Rg)))
        elif index == len(peps)/2: point = sub(center, (0, math.ceil(Rg)));
        elif index < len(peps)/2:
            point = add(center, (int(math.cos(math.radians(outangle))*(Rg)), int(math.sin(math.radians(outangle))*(Rg))))
            coords[index] = point
        else:
            point = (img.size[0]-coords[len(peps)-index][0],coords[len(peps)-index][1])
        if charts[server]["charts"][chart]["people"][person]["avatar"] != None:
            try:
                avatar = Image.open(charts[server]["charts"][chart]["people"][person]["avatar"])
                data = avatar.load()
                if avatar.mode == "RGBA":
                    for y in range(128):
                        for x in range(128):
                            if data[x, y][3] < 255:  data[x, y] = (255, 255, 255, 255)
            except: avatar = place;
        else:
            avatar = place
        img.paste(avatar, (int(point[0]-64), int(point[1]-64)), mask)
        box = [(int(point[0]-64), int(point[1]-64)),(int(point[0]+64), int(point[1]+64))]
        draw.ellipse(box, fill = None, outline = '#000000', width = 5)
        font = ImageFont.truetype('Inconsolata.otf', 14)
        name = person
        if len(name) > 25: name = name[0:16]+"..."
        size = font.getsize(name)
        if index <= len(peps)/4 or index >= len(peps)/4*3:
            textpoint = add(point, (-size[0]/2 , 64))
        else: textpoint = add(point, (-size[0]/2, -68-size[1]))
        draw.text(textpoint, name, '#000000', font)

    #main chart done, add legend
    used_keys = sorted(list(used_keys))
    k = len(used_keys)
    nk = math.ceil(k/sk) #number of key rows we will need to fit
    legend = Image.new("RGB", (222*nk, 24*sk), '#ffffff')
    for i in range(nk):
        for j in range(min(sk, k)):
            key = build_key(used_keys[i*sk+j], '#'+charts[server]["charts"][chart]["keys"][used_keys[i*sk+j]])
            legend.paste(key, (222*i, 24*j))
    #put two and two together
    result = Image.new("RGB", (legend.size[0]+img.size[0], img.size[1]))
    result.paste(legend)
    result.paste(img, (legend.size[0], 0))
    return result




def build_key(keyname, keycolor):
    if len(keyname) > 20: keyname = keyname[0:16]+"..."
    img = PIL.Image.new("RGB", (222, 24), '#ffffff')
    font = ImageFont.truetype('Inconsolata.otf', 18)
    draw = ImageDraw.Draw(img)
    draw.rectangle([4, 4, 21, 21], keycolor)
    draw.text((32, 3), keyname, '#000000', font)
    return img

@client.command(pass_context = True)
async def image_rel(ctx, chart = None, source = None, target = None):
    if chart == None or source == None or target == None:
        await client.send_message(ctx.message.channel, "Invalid arguments! Please input the name of the chart and the two names you wish to check.")
        return
    global charts
    server = ctx.message.server.id
    if not chart in charts[server]["charts"].keys():
        await client.send_message(ctx.message.channel, "Found no chart with this name!")
        return
    if not source in charts[server]["charts"][chart]["people"].keys():
        await client.send_message(ctx.message.channel, "There is nobody named " + source + " here!")
        return
    if not target in charts[server]["charts"][chart]["people"].keys():
        await client.send_message(ctx.message.channel, "There is nobody named " + target + " here!")
        return
    if not (source in charts[server]["charts"][chart]["people"][target]["rels"].keys() or target in charts[server]["charts"][chart]["people"][source]["rels"].keys()):
        await client.send_message(ctx.message.channel, "There is no connection between these two in this chart!")
        return
    await client.send_message(ctx.message.channel, "Validating chart...")
    t = valid(charts[server]["charts"][chart], "chart")
    if isinstance(t, Exception):
            out = io.BytesIO(str(t).encode('utf-8'))
            out.seek(0)
            await client.send_file(ctx.message.channel, out, filename = "error_log.txt", content = "Chart validation failed! Here are the error logs:")
            out.close()
            return
    else:
        await client.send_message(ctx.message.channel, "Pruned " + str(t) + " invalid entires...")
        font = ImageFont.truetype('Inconsolata.otf', 14)
        add = lambda xs,ys:(xs[0]+ys[0], xs[1]+ys[1]) #tuple summation
        sub = lambda xs,ys:(xs[0]-ys[0], xs[1]-ys[1]) #tuple subtraction

        if target in charts[server]["charts"][chart]["people"][source]["rels"].keys():
            key1 = charts[server]["charts"][chart]["people"][source]["rels"][target]["key"]
            color1 = '#' + charts[server]["charts"][chart]["keys"][key1]
            if len(key1) > 20: key1 = key1[0:16]+"..."
            desc1 = charts[server]["charts"][chart]["people"][source]["rels"][target]["desc"]
            if desc1 == None:
                desc1 = ""
            else:
                if len(desc1) > 100: desc1 = desc1[0:94]+"<...>"
                desc1 = ': "'+desc1+'"'
            desc1 = key1.title() + desc1
        else: desc1 = ""; color1 = "#ffffff"
        if source in charts[server]["charts"][chart]["people"][target]["rels"].keys():
            key2 = charts[server]["charts"][chart]["people"][target]["rels"][source]["key"]
            color2 = '#' + charts[server]["charts"][chart]["keys"][key2]
            if len(key2) > 20: key2 = key2[0:16]+"..."
            desc2 = charts[server]["charts"][chart]["people"][target]["rels"][source]["desc"]
            if desc2 == None:
                desc2 = ""
            else:
                if len(desc2) > 100: desc2 = desc2[0:94]+"<...>"
                desc2 = ': "'+desc2+'"'
            desc2 = key2.title() + desc2
        else: desc2 = ""; color2 = "#ffffff"
        text1 = font.getsize(desc1)
        text2 = font.getsize(desc2)
        length = max(text1[0], text2[0])
        size = (length+256, 150)

        img = Image.new("RGB", size, "#ffffff")
        draw = ImageDraw.Draw(img)

        draw.line([(56, 20), (size[0]-56, 20)], color1, width = 2)
        mid = (size[0]/2, 20)
        text1 = (text1[0]/2, text1[1]+5)
        textpoint = sub(mid, text1)
        draw.text(textpoint, desc1, "#000000", font)
        vector = (10, 0)
        offset = (0, 4)
        mid = add(mid, vector)
        draw.polygon([add(mid, vector), add(mid, offset), sub(mid, offset)], color1, color1)

        draw.line([(56, 113), (size[0]-56, 113)], color2, width = 2)
        mid = (size[0]/2, 113)
        textpoint = sub(mid,(text2[0]/2, -5))
        draw.text(textpoint, desc2, "#000000", font)
        vector = (-10, 0)
        offset = (0, 4)
        mid = add(mid, vector)
        draw.polygon([add(mid, vector), add(mid, offset), sub(mid, offset)], color2, color2)

        place = Image.open('placeholder.png')
        mask = Image.open('mask.png')

        if charts[server]["charts"][chart]["people"][source]["avatar"] != None:
            try:
                avatar = Image.open(charts[server]["charts"][chart]["people"][source]["avatar"])
                data = avatar.load()
                if avatar.mode == "RGBA":
                    for y in range(128):
                        for x in range(128):
                            if data[x, y][3] < 255:  data[x, y] = (255, 255, 255, 255)
            except: avatar = place;
        else:
            avatar = place
        img.paste(avatar, (5, 5), mask)
        box = [(5, 5), (133, 133)]
        draw.ellipse(box, fill = None, outline = '#000000', width = 5)
        text = source
        if len(text) > 20: text = text[0:16]+"..."
        tsize = font.getsize(text)
        textpoint = sub((69, 135), (tsize[0]/2, 0))
        draw.text(textpoint, text, "#000000", font)

        if charts[server]["charts"][chart]["people"][target]["avatar"] != None:
            try:
                avatar = Image.open(charts[server]["charts"][chart]["people"][target]["avatar"])
                data = avatar.load()
                if avatar.mode == "RGBA":
                    for y in range(128):
                        for x in range(128):
                            if data[x, y][3] < 255:  data[x, y] = (255, 255, 255, 255)
            except: avatar = place;
        else:
            avatar = place
        img.paste(avatar, (size[0]-133, 5), mask)
        box = [(size[0]-133, 5), (size[0]-5, 133)]
        draw.ellipse(box, fill = None, outline = '#000000', width = 5)
        text = target
        if len(text) > 20: text = text[0:16]+"..."
        tsize = font.getsize(text)
        textpoint = sub((size[0]-69, 135), (tsize[0]/2, 0))
        draw.text(textpoint, text, "#000000", font)

        bimg = io.BytesIO()
        img.save(bimg, "PNG")
        bimg.seek(0)
        await client.send_file(ctx.message.channel, bimg, filename = "rel.png", content = "Requested relationship in image form:")
        bimg.close()




def obtain_sheet_data(worksheet, startlabel, endlabel):
    label = worksheet.title + "!" + startlabel + ":" + endlabel

    resp = worksheet.spreadsheet.fetch_sheet_metadata({
        'includeGridData': True,
        'ranges': [label],
        'fields': 'sheets.data.rowData.values'
    })
    result = resp['sheets'][0]['data'][0]['rowData']
    return result if result else None

def obtain_prot(worksheet):
    label = worksheet.title + "!A1:A1"

    resp = worksheet.spreadsheet.fetch_sheet_metadata({
        'includeGridData': True,
        'ranges': [label],
        'fields': 'sheets'
    })
    return (resp['sheets'][0]['data'][0]['rowData'][0]["values"][0]["effectiveValue"]["stringValue"], resp['sheets'][0]["protectedRanges"])



async def autobackup():
    n = 0
    await client.wait_until_ready()
    while not client.is_closed:
        with open('charts.json', "r") as file:
            backup = json.load(file)
        with open('backup.json', "w") as output:
            json.dump(backup, output)
        n+= 1
        print("tick")
        if n == 4:
            n = 0
            for server, data in backup.items():
                if data["sheet"] == None: continue
                for name, chart in data["charts"].items():
                    print(name, chart)
                    try:
                        if chart['auto'] == True:
                            background_publish(backup, server, name)
                            print(name)
                    except Exception as error:
                        text = traceback.format_exception(type(error), error, error.__traceback__)
                        text = "".join(text)
                        print(text)
                        chart['auto'] = False
        await asyncio.sleep(900)


def background_publish(charts, server, name):
    t = valid(charts[server]["charts"][name], "chart")
    if isinstance(t, Exception):
            return
    else:
        people = len(charts[server]["charts"][name]["people"])
        keys = len(charts[server]["charts"][name]["keys"])
        sheets = charts[server]["sheet"]
        gclient.login()
        if sheets == None:
            return
        else:
            shobj = gclient.open_by_url(charts[server]["sheet"])
            with open('charts.json', 'w') as file:    #save it
                json.dump(charts, file)
        try:
            wobj = shobj.worksheet(name)
            wobj.resize(rows = 1)
            wobj.resize(cols = 1)   #avoid problems with resize formatting the hard way
            wobj.resize(rows = people+3)
            wobj.resize(cols = max(people+1,keys+1))
        except gspread.exceptions.WorksheetNotFound:
            wobj = shobj.add_worksheet(name, people+3, max(people+1,keys+1))
        try:
            shobj.del_worksheet(shobj.worksheet("Sheet1"))
        except: pass
        wid = wobj.id

        ucreq = {"rows" : [], "fields":"*", "start" : {
                                            "sheetId":wid,
                                            "rowIndex":0,
                                            "columnIndex":0
                                            }
        }
        #first row - blank first cell, rest are names in bold
        firstrow = {"values" : []}
        basiccell = {"userEnteredValue":{"stringValue":""},"userEnteredFormat":{"backgroundColor":{"red":1,"blue":1,"green":1},"textFormat":{"foregroundColor":{"red":0,"blue":0,"green":0},"bold":True}} }
        blacktile = {"userEnteredValue":{"stringValue":""},"userEnteredFormat":{"backgroundColor":{"red":0,"blue":0,"green":0},"textFormat":{"foregroundColor":{"red":1,"blue":1,"green":1},"bold":True}} }
        startcell = {"userEnteredValue":{"stringValue":"#RelBot|"+server+"|"+name},"userEnteredFormat":{"backgroundColor":{"red":1,"blue":1,"green":1},"textFormat":{"foregroundColor":{"red":0,"blue":0,"green":0},"bold":True}} }
        firstrow["values"].append(startcell)
        bcellcopy = copy.deepcopy(basiccell)
        for k in sorted(charts[server]["charts"][name]["people"].keys()):
            bcellcopy["userEnteredValue"]["stringValue"] = k;
            firstrow["values"].append(copy.deepcopy(bcellcopy))
        ucreq["rows"].append(copy.deepcopy(firstrow))
        #next rows - start with name, fill out rels
        peps = sorted(list(charts[server]["charts"][name]["people"].keys()))
        for person, values in sorted(charts[server]["charts"][name]["people"].items()):
            personrow = {"values" : []}                           # [
            startcell = copy.deepcopy(basiccell)                  # [
            startcell["userEnteredValue"]["stringValue"] = person # [ places name
            personrow["values"].append(copy.deepcopy(startcell))  # [
            for pos in peps:
                #iterate over the list of people - if there is a rel for them, make it happen, else placeholder
                relcell = copy.deepcopy(basiccell)

                if pos in values["rels"].keys():    #there is a rel - grab the rel's color
                    colors = scale_rgb_tuple(hex_to_rgb(charts[server]["charts"][name]["keys"][values["rels"][pos]["key"]]))
                    relcell["userEnteredFormat"]["backgroundColor"]={
                                    "red": colors[0],         #
                                    "blue": colors[2],        #enter it in
                                    "green": colors[1]        #
                    }
                    lum = (colors[0]*0.299 + colors[1]*0.587 + colors[2]*0.114)
                    if lum > 0.5: lum = 0     #calculate luminocity and choose contrary text color
                    else: lum = 1
                    relcell["userEnteredFormat"]["textFormat"]["foregroundColor"]={
                                    "red": lum,
                                    "blue": lum,
                                    "green": lum
                    }
                    if values["rels"][pos]["desc"] != None:
                        relcell["userEnteredValue"]["stringValue"]=values["rels"][pos]["desc"]
                    else:
                        relcell["userEnteredValue"]["stringValue"]=values["rels"][pos]["key"].title()  #insert rel name
                elif pos == person:      #this is the relperson - insert blacktile with motto
                    btile =  copy.deepcopy(blacktile)
                    if values["motto"]!=None:
                        btile["userEnteredValue"]["stringValue"]=values["motto"]
                    relcell = copy.deepcopy(btile)
                else:                      #this is no rel - insert placeholder
                    relcell["userEnteredFormat"]["backgroundColor"]={
                                    "red": 0.8,
                                    "blue": 0.8,
                                    "green": 0.8
                    }
                    relcell["userEnteredValue"]["stringValue"]="Haven't Met"
                personrow["values"].append(relcell)
            ucreq["rows"].append(copy.deepcopy(personrow))
        #rel rows placed, place border
        personrow = {"values" : []}
        for i in range(max(people+1, keys+1)):
            personrow["values"].append(blacktile)
        ucreq["rows"].append(copy.deepcopy(personrow))
        #border placed, place key row
        personrow = {"values" : []}
        personrow["values"].append(basiccell)
        personrow["values"][0]["userEnteredValue"]["stringValue"]="Chart keys:"
        for key, color in charts[server]["charts"][name]["keys"].items():
            colorcell = copy.deepcopy(basiccell)
            colors = scale_rgb_tuple(hex_to_rgb(color)) #acquire key color
            colorcell["userEnteredFormat"]["backgroundColor"]={
                            "red": colors[0],         #
                            "blue": colors[2],        #enter it in
                            "green": colors[1]        #
            }
            lum = (colors[0]*0.299 + colors[1]*0.587 + colors[2]*0.114)
            if lum > 0.5: lum = 0     #calculate luminocity and choose contrary text color
            else: lum = 1
            colorcell["userEnteredFormat"]["textFormat"]["foregroundColor"]={
                            "red": lum,
                            "blue": lum,
                            "green": lum
            }
            colorcell["userEnteredValue"]["stringValue"]=key  #insert key name
            personrow["values"].append(copy.deepcopy(colorcell))
        ucreq["rows"].append(copy.deepcopy(personrow))
        #all rows placed - request formed
        protreq = {"range":{
                        "sheetId" : wid,
                        "startRowIndex" : 0,
                        "startColumnIndex" : 0,
                        "endRowIndex" : 1,
                        "endColumnIndex" : 1
        }, "warningOnly" : False,
           "editors" : {
                        "users" : ["relbot@relbot-230215.iam.gserviceaccount.com"]
        }
        }
        request = {"requests":[{"updateCells": ucreq},{"addProtectedRange": {"protectedRange": protreq}}]};
        #...and we send it as a batch, cause I ain't rewriting the shit above to make it adhere to update_cells
        shobj.batch_update(request)




def run_client(client, token):
    t = False
    e = None
    while True:
        try:
            e = None
            client.loop.create_task(autobackup())
            client.run(token)
        except (KeyboardInterrupt, SystemExit):
            t = True
        except Exception as e:
            if not t: print("Error", e)  # or use proper logging
        finally:
            if t or (e == None):
                return
            else:
                print("Waiting until restart")
                time.sleep(30)

run_client(client, token)
