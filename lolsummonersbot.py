# modules
import os
import time
import json
import codecs
import MySQLdb
import logging
import requests
from time import sleep
from html.parser import HTMLParser
from telegram.ext import MessageHandler, Filters, Updater, CommandHandler, InlineQueryHandler, CallbackQueryHandler, Job
from telegram import InlineQueryResultArticle, InputTextMessageContent, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ReplyKeyboardMarkup
# variables (and technically functions)
    # keys, tokens and passwords
os.chdir("/home/zlyfer/TelegramBots/lolsummonersbot/")
with codecs.open('bot_token.ini', 'r', 'utf-8') as bottoken_file:
    bottoken = bottoken_file.read()
with codecs.open('api_key.ini', 'r', 'utf-8') as apikey_file:
    apikey = apikey_file.read()
with codecs.open('sql_password.ini', 'r', 'utf-8') as sql_password_file:
    mysqlpw = sql_password_file.read()
    # keyboards
MainKeyboard = [[KeyboardButton("Check Ingame")], [KeyboardButton("Notifications")], [KeyboardButton("Add Summoner"), KeyboardButton("Remove Summoner")]]
BackKeyboard = [[KeyboardButton("Back")]]
    # misc
WhatToDo = {}
Regions = ["BR", "EUNE", "EUW", "JP", "KR", "LAN", "LAS", "NA", "OCE", "TR", "RU"]#, "PBE"]
Servers = {"BR": "br1", "EUNE": "eun1", "EUW": "euw1", "JP": "jp1", "KR": "kr", "LAN": "la1", "LAS": "la2", "NA": "na1", "OCE": "oc1", "TR": "tr1", "RU": "ru"}#, "PBE": "pbe1"}
NotificationIcons = ["🔇", "🔊"]
NotificationIndex = {0: 1, 1: 0}
#

# misc
logging.basicConfig(format="\n%(levelname)s: @'%(asctime)s' in '%(name)s':\n> %(message)s", level=logging.INFO)
updater = Updater(token=bottoken)
#

# notes
    # WhatToDo Codes
        # No Index
        # 1 Registration
            # Main Index
            # 2 Add Summoner
            # 3 Remove Summoner
            # 4 Check Ingame
                # Sub Index
                # 
#

# misc functions
def misc_s2hms(seconds):
    hms = []
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    hms.append("%02d" % hours)
    hms.append("%02d" % minutes)
    hms.append("%02d" % seconds)
    return (hms)

def misc_e2hms(milliseconds):
    return (misc_s2hms((int(time.time())) - (milliseconds / 1000)))

def misc_summonerzone(summonerzone):
    if len(summonerzone) > 2:
        summoner = ""
        index = -1
        for entry in summonerzone:
            index+=1
            if entry == summonerzone[-1:][0]:
                if index != int(len(summonerzone)-1):
                    summoner += entry + " "
            else:
                    summoner += entry + " "
        return ([summoner[:-1], summonerzone[-1:][0]])
    else:
        return (summonerzone)
#

# api functions
def api_ids(name, zone):
    if not zone.upper() in Regions:
        return (False)
    url = "https://" + Servers[zone.upper()] + ".api.riotgames.com" + "/lol/summoner/v3/summoners/by-name/" + name + "?api_key=" + apikey
    session = requests.session()
    response = json.loads(session.get(url).text)
    if 'id' in response:
        return ({'id': str(response['id']), 'accountid': str(response['accountId'])})
    else:
        return (False)

def api_spectator(name, zone):
    if not zone.upper() in Regions:
        return (False)
    url = "https://" + Servers[zone.upper()] + ".api.riotgames.com" + "/lol/spectator/v3/active-games/by-summoner/" + str(api_ids(name, zone)['id']) + "?api_key=" + apikey
    session = requests.session()
    response = json.loads(session.get(url).text)
    if 'gameId' in response:
        return (response)
    else:
        return (False)
#

# mysql functions
def mysql_connect():
    db = False
    while True:
        try:
            db=MySQLdb.connect(host="127.0.0.1", user="root", passwd=mysqlpw, db="lolsummonersbot")
        except MySQLdb.Error:
            os.system("systemctl restart mysql")
            sleep(5)
        else:
            break
    return (db)

def mysql_adduser(chat_id, summoner_name, zone):
    db = mysql_connect()
    cur = db.cursor()
    cur.execute("INSERT IGNORE INTO `users` (`chat_id`, `summoner_name`, `region`) VALUES ('%s', '%s', '%s')" % (chat_id, summoner_name, zone))
    cur.execute("CREATE TABLE IF NOT EXISTS `lolsummonersbot`.`friendlist_%s` (`summoner_name` CHAR(255) NOT NULL , `zone` CHAR(255) NOT NULL, `notification` INT NULL DEFAULT '0', UNIQUE (`summoner_name`, `zone`)) ENGINE = InnoDB" % chat_id)
    db.commit()
    db.close
    return

def mysql_friendlistadd(chat_id, summoner_name, zone):
    db = mysql_connect()
    cur = db.cursor()
    cur.execute("INSERT IGNORE INTO `friendlist_%s` (`summoner_name`, `zone`) VALUES ('%s', '%s')" % (chat_id, summoner_name, zone))
    db.commit()
    db.close
    return
    
def mysql_friendlistrem(chat_id, summoner_name, zone):
    db = mysql_connect()
    cur = db.cursor()
    cur.execute("DELETE FROM `friendlist_%s` WHERE `summoner_name`='%s' AND `zone`='%s'" % (chat_id, summoner_name, zone))
    db.commit()
    db.close
    return

def mysql_friendlistget(chat_id):
    db = mysql_connect()
    cur = db.cursor()
    cur.execute("SELECT * FROM `friendlist_%s`" % chat_id)
    friendlist = []
    for row in cur.fetchall():
        friendlist.append({'summoner_name': row[0], 'zone': row[1], 'notification': row[2]})
    db.close
    if friendlist == []:
        return (False)
    else:
        return (friendlist)

def mysql_checkregister(chat_id):
    db = mysql_connect()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM `users` WHERE `chat_id`='%s'" % chat_id)
    amount = cur.fetchone()[0]
    db.close
    if amount == 0:
        return (False)
    elif amount == 1:
        return (True)
    else:
        return ("ERROR")

def mysql_tooglenotification(chat_id, summoner_name, zone):
    db = mysql_connect()
    cur = db.cursor()
    cur.execute("SELECT `notification` FROM `friendlist_%s` WHERE `summoner_name`='%s' and `zone`='%s'" % (chat_id, summoner_name, zone))
    currentindex = cur.fetchone()
    if currentindex != None:
        cur.execute("UPDATE `friendlist_%s` SET `notification`=%s WHERE `summoner_name`='%s' and `zone`='%s'" % (chat_id, NotificationIndex[currentindex[0]], summoner_name, zone))
        db.commit()
        db.close
        return ([summoner_name, zone, NotificationIndex[currentindex[0]]])
    else:
        db.commit()
        db.close
        return (False)
#

# bot system functions
def bot_keyboardgen(chat_id, keyboard):
    if keyboard == "FriendlistKeyboard":
        global FriendlistKeyboard
        FriendlistKeyboard = []
        friendlist = mysql_friendlistget(chat_id)
        if not friendlist == False:
            for summoner in friendlist:
                FriendlistKeyboard.append([KeyboardButton("%s %s" % (summoner['summoner_name'], summoner['zone']))])
        FriendlistKeyboard.append(BackKeyboard[0])
    elif keyboard == "NotificationKeyboard":
        global NotificationKeyboard
        NotificationKeyboard = []
        friendlist = mysql_friendlistget(chat_id)
        if not friendlist == False:
            for summoner in friendlist:
                NotificationKeyboard.append([KeyboardButton("%s %s %s" % (summoner['summoner_name'], summoner['zone'], NotificationIcons[summoner['notification']]))])
        NotificationKeyboard.append(BackKeyboard[0])
    else:
        return (False)
    return (True)
#

# job system functions
def job_notification(bot, job):
    db = mysql_connect()
    cur_chat_id = db.cursor()
    cur_friendlist = db.cursor()
    cur_chat_id.execute("SELECT `chat_id` FROM `users` WHERE 1")
    for chat_id in cur_chat_id.fetchall():
        cur_friendlist.execute("SELECT * FROM `friendlist_%s` WHERE `notification`!=0" % chat_id[0])
        for friendlist_entry in cur_friendlist.fetchall():
            sleep(1)
            summoner_name = friendlist_entry[0]
            zone = friendlist_entry[1]
            if friendlist_entry[2] == 1:
                ingame = api_spectator(summoner_name, zone)                
                if ingame != False:
                    ingame = misc_e2hms(ingame['gameStartTime'])
                    bot.sendMessage(chat_id=chat_id[0], parse_mode="HTML", text="<strong>NOTIFICATION</strong>: The summoner <strong>%s</strong> from region <strong>%s</strong> is ingame since <strong>%s hours</strong>, <strong>%s minutes</strong> and <strong>%s seconds</strong>." % (summoner_name, zone, ingame[0], ingame[1], ingame[2]))
        sleep(1)
    return
#

# bot communication functions
def bot_main(bot, update):
    bot.sendMessage(chat_id=-248828335, parse_mode="HTML", text="<strong>%s/%s/%s/%s</strong>: <i>%s</i>" % (update.message.chat.username, update.message.chat.first_name, update.message.chat_id, update.message.from_user.language_code, update.message.text))
    bot.send_chat_action(chat_id=update.message.chat_id, action="TYPING")

    chat_id = update.message.chat_id
    text = update.message.text
    bot_started = False

    if chat_id in WhatToDo:
        if WhatToDo[chat_id] == 1:
            bot_started = True
    else:
        WhatToDo[chat_id] = 0
    if mysql_checkregister(chat_id) == False and bot_started == False:
        bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Hello, please send me your summoner name and your region so I can register you.\nExample: <strong>zIyf3r euw</strong>")
        WhatToDo[chat_id] = 1
        return
    if text == "/start":
        bot.sendMessage(chat_id=chat_id, text="Welcome.", reply_markup=ReplyKeyboardMarkup(MainKeyboard))
        if WhatToDo[chat_id] == 1:
            bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Please send me your summoner name and your region so I can register you.\nExample: <strong>zIyf3r euw</strong>")
        else:
            WhatToDo[chat_id] = 0
        return
    elif text == "Add Summoner" and WhatToDo[chat_id] != 1:
        bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Okay, send me the summoner name and the region so I can add the summoner for you.\nExample: <strong>zIyf3r euw</strong>", reply_markup=ReplyKeyboardMarkup(BackKeyboard))
        WhatToDo[chat_id] = 2
        return
    elif text == "Remove Summoner" and WhatToDo[chat_id] != 1:
        bot_keyboardgen(chat_id, "FriendlistKeyboard")
        bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Okay, send me the summoner name and the region so I can remove the summoner for you.\nExample: <strong>zIyf3r euw</strong>", reply_markup=ReplyKeyboardMarkup(FriendlistKeyboard))
        WhatToDo[chat_id] = 3
        return
    elif text == "Check Ingame" and WhatToDo[chat_id] != 1:
        bot_keyboardgen(chat_id, "FriendlistKeyboard")
        bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Okay, please select a summoner. You can write the summoner name and region manually instead as well.\nExample: <strong>zIyf3r euw</strong>", reply_markup=ReplyKeyboardMarkup(FriendlistKeyboard))
        WhatToDo[chat_id] = 4
        return
    elif text == "Notifications" and WhatToDo[chat_id] != 1:
        bot_keyboardgen(chat_id, "NotificationKeyboard")
        bot.sendMessage(chat_id=chat_id, text="Please select a summoner to toggle ingame notification.", reply_markup=ReplyKeyboardMarkup(NotificationKeyboard))
        WhatToDo[chat_id] = 5
        return
    elif text == "Back" and WhatToDo[chat_id] != 1:
        bot.sendMessage(chat_id=chat_id, text="Okay, back.", reply_markup=ReplyKeyboardMarkup(MainKeyboard))
        WhatToDo[chat_id] = 0
        return
    else:
        if WhatToDo[chat_id] == 0:
            bot.sendMessage(chat_id=chat_id, text="Sorry, I didn't understand that.")
            return

        elif WhatToDo[chat_id] == 1:
            if len(misc_summonerzone(text.split())) == 2:
                summoner_name = misc_summonerzone(text.split())[0]
                zone = misc_summonerzone(text.split())[1]
                if zone.upper() in Regions:
                    if api_ids(summoner_name, zone) != False:
                        mysql_adduser(chat_id, summoner_name, zone)
                        WhatToDo[chat_id] = 0
                        bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="You have been registered as <strong>%s</strong> from region <strong>%s</strong>." % (summoner_name, zone), reply_markup=ReplyKeyboardMarkup(MainKeyboard))
                        return
                    else:
                        bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="The summoner <strong>%s</strong> from region <strong>%s</strong> doesn't seem to exist." % (summoner_name, zone))
                        return
                else:
                    bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="The region <strong>%s</strong> is invalid." % zone)
                    return
            else:
                bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Please send me at least two words like following example:\n<strong>zIyf3r euw</strong>")
                return

        elif WhatToDo[chat_id] == 2:
            text = misc_summonerzone(text.split())
            if len(text) == 2:
                if text[1].upper() in Regions:
                    if api_ids(text[0], text[1]) != False:
                        mysql_friendlistadd(chat_id, text[0], text[1])
                        bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Okay, the summoner <strong>%s</strong> from region <strong>%s</strong> has been added." % (text[0], text[1]))
                        return
                    else:
                        bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Sorry, the summoner <strong>%s</strong> doesn't seem to exist." % text[0])
                        return
                else:
                    bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Sorry, the region <strong>%s</strong> is invalid." % text[1])
                    return
            else:
                bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Sorry, you are supposed to send me the summoner name and the region - at least two words.\nExample: <strong>zIyf3r euw</strong>")
                return

        elif WhatToDo[chat_id] == 3:
            text = misc_summonerzone(text.split())
            if len(text) == 2:
                friendlist = mysql_friendlistget(chat_id)
                found = False
                for entry in friendlist:
                    if text[0] == entry['summoner_name'] and text[1] == entry['zone']:
                        found = True
                        mysql_friendlistrem(chat_id, text[0], text[1])
                        bot_keyboardgen(chat_id, "FriendlistKeyboard")
                        bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Okay, I removed the summoner <strong>%s</strong> from region <strong>%s</strong> from your summoners list." % (text[0], text[1]), reply_markup=ReplyKeyboardMarkup(FriendlistKeyboard))
                        return
                if found == False:
                    bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Sorry, the summoner <strong>%s</strong> from region <strong>%s</strong> is not part of your summoners list." % (text[0], text[1]))
                    return
            else:
                bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Sorry, you are supposed to send me the summoner name and the region - at least two words.\nExample: <strong>zIyf3r euw</strong>")
                return
            return

        elif WhatToDo[chat_id] == 4:
            if misc_summonerzone(text.split())[1].upper() in Regions:
                if api_ids(misc_summonerzone(text.split())[0], misc_summonerzone(text.split())[1]) != False:
                    request = api_spectator(misc_summonerzone(text.split())[0], misc_summonerzone(text.split())[1])
                    if request == False:
                        bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="<strong>%s</strong> is currently not ingame." % misc_summonerzone(text.split())[0])
                    else:
                        time = misc_e2hms(request['gameStartTime'])
                        bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="<strong>%s</strong> is ingame since <strong>%s hours</strong>, <strong>%s minutes</strong> and <strong>%s seconds</strong>." % (misc_summonerzone(text.split())[0], time[0], time[1], time[2]))
                else:
                    bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Sorry, the summoner <strong>%s</strong> doesn't seem to exist." % misc_summonerzone(text.split())[0])
            else:
                bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Sorry, the region <strong>%s</strong> is invalid." % misc_summonerzone(text.split())[1])
            return

        elif WhatToDo[chat_id] == 5:
            text = misc_summonerzone(text[:-1].split())
            if not len(text) == 2:
                bot.sendMessage(chat_id=chat_id, text="There was an error updating your notifications please restart the bot.", reply_markup=ReplyKeyboardMarkup(NotificationKeyboard))
                return
            answer = mysql_tooglenotification(chat_id, text[0], text[1])
            bot_keyboardgen(chat_id, "NotificationKeyboard")
            if answer == False:
                bot.sendMessage(chat_id=chat_id, text="There was an error updating your notifications please restart the bot.", reply_markup=ReplyKeyboardMarkup(NotificationKeyboard))
            else:
                bot.sendMessage(chat_id=chat_id, parse_mode="HTML", text="Ingame notifciation for summoner <strong>%s</strong> from region <strong>%s</strong> has been <strong>%s</strong>." % (answer[0], answer[1], {0: "disabled", 1: "enabled"}[answer[2]]), reply_markup=ReplyKeyboardMarkup(NotificationKeyboard))
            return

        else:
            bot.sendMessage(chat_id=chat_id, text="Sorry, I didn't understand that.")
            return
    return
#

# handler & jobs
updater.dispatcher.add_handler(CommandHandler('start', bot_main))
updater.dispatcher.add_handler(MessageHandler(Filters.text, bot_main))
updater.job_queue.run_repeating(job_notification, interval=1800, first=0)
#

# bot start
updater.start_polling()
updater.idle()
#