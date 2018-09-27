#!/usr/bin/python3

"""

Parses the given feed, and if there is a new post it sends the content
to a Telegram user through a bot. It is supposed to run continuously.

"""

import sys
import time
import calendar

sys.path.insert(0, "/home/fmarotta/raspbotpi/lib/python3.7")
import telepot
from bs4 import BeautifulSoup # Install package ``beautifulsoup4'' via pip.
import feedparser

#if len(sys.argv) != 3:
    #print('Usage: python rss.py <bot\'s token> <your Telegram ID>')
    #sys.exit()

# Initialize the bot
with open('/home/fmarotta/raspbotpi/config/params') as params_file:
    lines = params_file.readlines()
    params = lines[0]
    params = params.rstrip("\n").split("\t")

token = params[0]
my_id = params[1]
bot = telepot.Bot(token)

# Define the feeds you want to "subscribe" to FIXME: read them from a
# file, or better yet let the user tell the bot which feeds he wants to
# read
feeds = [
    'http://www.lescienze.it/rss/all/rss2.0.xml',
    'https://www.archlinux.org/feeds/news/',
    'https://superuser.com/feeds/question/1343807',
]
#feeds = [
#    'http://www.lescienze.it/rss/all/rss2.0.xml',
#    'https://www.debian.org/News/news',
#    'https://www.archlinux.org/feeds/news/',
#]

# The first time the program is executed, set last_item to an empty
# string.
last_item = []
for feed in feeds:
    last_item.insert(feeds.index(feed), '')

# Define the feed parser
def parse_feed(feed):
    # Variable definitions
    msg = []
    global last_item

    # Parse the feed and return if there are errors
    d = feedparser.parse(feed)
    if d.status != 200:
        bot.sendMessage(my_id, 'An http error occurred while parsing the feed {}.'.format(feed))
        return [] # This prevents updating last_item, which stays as it was the last time the feed was parsed without errors
    if d.bozo:
        bot.sendMessage(my_id, 'A parsing error occurred while parsing the feed {}.'.format(feed)) # Do not return: perhaps the error is not fatal. Besides, the error will persist as long as the faulty post stays in the feed

    for entry in d.entries:
        if 'title' in d.feed:
            feed_title = d.feed.title
        else:
            feed_title = 'No title for this feed'
        if 'title' in entry:
            entry_title = entry.title
        else:
            entry_title = 'No title for this entry'
        if 'description' in entry:
            entry_description = entry.description
            soup = BeautifulSoup(entry_description, 'html5lib')
            entry_description = soup.get_text(' ')
        else:
            entry_description = 'No description for this entry'
        if 'link' in entry:
            entry_link = entry.link
        else:
            entry_link = 'No link for this entry'

        # Check if we haven't already seen this update
        if entry_link != last_item[feeds.index(feed)] and last_item[feeds.index(feed)] != '':
            msg.insert(0, '<b>Feed update!\n{}</b>\n\n<i>{}</i>\n\n{}\n\nLink:\n{}'.format(feed_title, entry_title, entry_description, entry_link))
        else:
            break

    # Update last_item with the latest item of the feed
    last_item[feeds.index(feed)] = d.entries[0].link

    return msg

while 1:
    for feed in feeds:
        msg = parse_feed(feed)
        for mex in msg:
            try:
                bot.sendMessage(my_id, mex, 'HTML')
            except telepot.exception.TelegramError as err:
                bot.sendMessage(my_id, 'There is a feed update from {}, but I cannot send it to you because of a Telegram error: {}'.format(feed, err))
    time.sleep(61 * 60)
