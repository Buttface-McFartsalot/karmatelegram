#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple karma bot for Telegram
# This program is dedicated to the public domain under the CC0 license.

"""
Usage:
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import logging
import os
import re
import sqlite3

# Enable logging
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)

logger = logging.getLogger(__name__)


conn = sqlite3.connect("karma.db", check_same_thread=False)
cur = conn.cursor()


def init_database():
    cur.execute("CREATE TABLE groups (group_id integer PRIMARY KEY)")
    cur.execute("CREATE TABLE users (username text PRIMARY KEY, first_name text, last_name text)")
    cur.execute("CREATE TABLE karma (karma integer, username text, group_id integer, FOREIGN KEY(group_id) REFERENCES groups(group_id), FOREIGN KEY(username) REFERENCES users(username))")
    conn.commit()
    conn.close()


def user_exists(username):
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cur.fetchone()
    return True if user else False


def user_create(username):
    cur.execute("INSERT INTO users (username) VALUES (?)", (username,))
    conn.commit()


def group_exists(group_id):
    cur.execute("SELECT * FROM groups WHERE group_id=?", (group_id,))
    group = cur.fetchone()
    return True if group else False


def group_create(group_id):
    cur.execute("INSERT INTO groups (group_id) VALUES (?)", (group_id,))
    conn.commit()


def karma_exists(username, group_id):
    cur.execute("SELECT * FROM karma WHERE username=? AND group_id=?", (username, group_id,))
    karma = cur.fetchone()
    return True if karma else False


def karma_create(username, group_id):
    cur.execute("INSERT INTO karma (username, group_id, karma) VALUES ((SELECT username FROM users WHERE username=?), (SELECT group_id FROM groups WHERE group_id=?), 0)", (username, group_id))
    conn.commit()


def karma_increment(username, group_id):
    if not user_exists(username): 
        user_create(username)
    if not group_exists(group_id): 
        group_create(group_id)
    if not karma_exists(username, group_id): 
        karma_create(username, group_id)
    cur.execute("update karma set karma=(karma+1) where username=? and group_id=?", (username, group_id))
    conn.commit()


def karma_decrement(username, group_id):
    if not user_exists(username): 
        user_create(username)
    if not group_exists(group_id): 
        group_create(group_id)
    if not karma_exists(username, group_id): 
        karma_create(username, group_id)
    cur.execute("update karma set karma=(karma-1) where username=? and group_id=?", (username, group_id))
    conn.commit()


def user_karma(username, group_id):
    cur.execute("SELECT * FROM karma WHERE username=? and group_id=?", (username, group_id))
    result = cur.fetchone()
    return result[0] if result else None
    

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Hi!')


def help(bot, update):
    help_message = """/upvote @username 
/downvote @username
/top5 local (on current group chat)
/top5 global (overall rating)
/rating @username
"""
    bot.sendMessage(update.message.chat_id, text=help_message)


def upvote(bot, update, args):
    from_user = update.message.from_user.name
    text = update.message.text
    chat_id = update.message.chat_id
    m = re.match("/upvote[ ]+(@[a-zA-Z_\digit]+)", text) 
    if not m:
        bot.sendMessage(chat_id, "%s Use \"/upvote @username\" for upvoting." % from_user)
        return
    to_user = m.groups()[0]
    if from_user == to_user:
        bot.sendMessage(chat_id, "%s You can't upvote or downvote yourself!" % from_user)
        return
    karma_increment(to_user, chat_id)


def downvote(bot, update, args):
    from_user = update.message.from_user.name
    text = update.message.text
    chat_id = update.message.chat_id
    m = re.match("/downvote[ ]+(@[a-zA-Z_\digit]+)", text) 
    if not m:
        bot.sendMessage(chat_id, "%s Use \"/downvote @username\" for downvoting." % from_user)
        return
    to_user = m.groups()[0]
    if from_user == to_user:
        bot.sendMessage(chat_id, "%s You can't upvote or downvote yourself!" % from_user)
        return
    karma_decrement(to_user, chat_id)


def rating(bot, update, args):
    from_user = update.message.from_user.name
    text = update.message.text
    chat_id = update.message.chat_id
    m = re.match("/rating[ ]+(@[a-zA-Z_\digit]+)", text) 
    if not m:
        bot.sendMessage(chat_id, "%s Use \"/rating @username\" for getting user's rating." % from_user)
        return
    requested_user = m.groups()[0]
    karma = user_karma(requested_user, chat_id)
    if karma:
        bot.sendMessage(chat_id, "%s's karma is %s." % (requested_user, karma))
    else:
        bot.sendMessage(chat_id, "%s doesn't have karma yet." % requested_user) 


def echo(bot, update, args):
    bot.sendMessage(update.message.chat_id, text=update.message.text)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    # Create the EventHandler and pass it your bot's token.
    token = os.environ.get("KARMABOT_TOKEN")
    if not token:
        print "KARMABOT_TOKEN environment variable is not set. Exit."
        sys.exit(1)

    updater = Updater(token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("upvote", upvote, pass_args=True))
    dp.add_handler(CommandHandler("downvote", downvote, pass_args=True))
    dp.add_handler(CommandHandler("rating", rating, pass_args=True))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler([Filters.text], echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
