"""

Parses the given feed, and if there is a new post it sends the content
to a Telegram user through a bot. It is supposed to run continuously.

"""

import telepot
import feedparser
import sys
import time
import calendar
from bs4 import BeautifulSoup

if len(sys.argv) != 3:
    print('Usage: python rss.py <bot\'s token> <your Telegram ID>')
    sys.exit()

# Initialize the bot
token = sys.argv[1]
my_id = sys.argv[2]
bot = telepot.Bot(token)

# Define the feeds you want to "subscribe" to
# FIXME: read them from a file, or better yet let the user tell the bot
# which feeds he wants to read
feeds = [
    'https://www.debian.org/News/news',
    'https://www.archlinux.org/feeds/news/',
]

# The first time the program is executed, set last_parsed_time to the
# current time
# Feature: let the user choose the time after which retrieve the posts
last_parsed_time = time.time()

# Define the feed parser
def parse_feed(feed):
    # Variable definitions
    msg = []
    global last_parsed_time

    # Save the time JUST BEFORE the feed is parsed
    parsed_time = time.time()
    # Parse the feed
    d = feedparser.parse(feed)
    for entry in d.entries:
        # Check if we have already seen this update
        if calendar.timegm(entry.updated_parsed) < last_parsed_time:
            continue
        # Otherwise send a message to the user
        else:
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

        msg.insert(0, '*Feed update!\n{}*\n\n_{}_\n\n{}\n\nLink:\n{}'.format(feed_title, entry_title, entry_description, entry_link))

    # Update last_parsed_time with the time of the parsing
    last_parsed_time = parsed_time

    return msg

while 1:
    for feed in feeds:
        msg = parse_feed(feed)
        for mex in msg:
            try:
                bot.sendMessage(my_id, mex, 'Markdown')
            except telepot.exception.TelegramError:
                bot.sendMessage(my_id, 'There is a feed update from {}, but I cannot send it to you because of a Telegram error'.format(feed))
    # Check for updates every 61 minutes
    time.sleep(61 * 60)

