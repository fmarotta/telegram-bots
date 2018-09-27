#!/usr/bin/python3

"""

This program connects to an imap account, fetches the unread emails
and sends the plain text parts to a Telegram user through a bot.

"""

# NOTE: telepot version > 7.1 has a problem with urrlib: see
# https://github.com/nickoala/telepot/issues/87
# In order for the bot to work properly, you should install telepot 7.0 with
# `pip install telepot==7.0`

import ssl
import imaplib
import email
import sys
import os
import time
from email.header import decode_header

sys.path.insert(0, "/home/fmarotta/raspbotpi/lib/python3.7")
import telepot
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from bs4 import BeautifulSoup # Install package ``beautifulsoup4'' via pip.

#if len(sys.argv) != 3:
#    print('Usage: python mail.py <bot\'s token> <your Telegram ID>')
#    sys.exit()

# Initialize the bot
with open('/home/fmarotta/raspbotpi/config/params') as params_file:
    lines = params_file.readlines()
    params = lines[0]
    params = params.rstrip("\n").split("\t")

token = params[0]
my_id = params[1]
bot = telepot.Bot(token)

# Define the mail account class
class ImapAccount:
    def __init__(self, imap_params):
        self.host = imap_params[0]
        self.port = imap_params[1]
        self.username = imap_params[2]
        self.password = imap_params[3]
        self.folders = imap_params[4].split(",")

# Define the accounts
# Feature: let the bot ask the user for new accounts
# NOTE: create a file named `mail_accounts' (without quotes) in a directory
# called `config' (without quotes); the directory should be in the same
# directory parent of this script. Fill the mail_accounts file with the
# information about your imap account with the following format:
# mailserver    port    username    password    folder,folder
# the values are tab-delimited. If you have more than one account, add other
# lines. A description of the fields follows:
# mailserver is the server which provides you the email service;
# port is the port through which the server is accessed;
# username is your account's username;
# password is your account's password (in clear);
# folder is one of the folders you want to read, tipically it is inbox. If you want to add more, separe them with a comma.
# Note that these are the same information that you have to enter in order to
# configure any mail client.
# Example:
# imap.gmail.com    993 john@gmail.com  qwerty123   inbox,spam
accounts = []
with open('/home/fmarotta/raspbotpi/config/mail_accounts') as mail_accounts:
    lines = mail_accounts.readlines()
    for imap_params in lines:
        imap_params = imap_params.rstrip("\n")
        accounts.append(ImapAccount(imap_params.split("\t")))


def search_email(mail, folder):
    # Select the specified folder
    result, n_mails = mail.select(folder)
    if result != 'OK':
        return result

    result, uids = mail.uid('search', None, '(UNSEEN)')
    if result != 'OK':
        return result

    return 'OK', uids


def imap_connect(account):
    # Create a ssl context for the connection to the imap server
    try:
        context = ssl.create_default_context()
    except ssl.SSLError as err:
        return 1, err

    # Connect to the server
    try:
        mail = imaplib.IMAP4_SSL(host=account.host, port=account.port, ssl_context=context)
    except IMAP4.error as err:
        return 1, err

    # Login to the specified account
    result, address = mail.login(account.username, account.password)
    if result != 'OK':
        return 1, result

    return 'OK', mail


def parse_email(mail, uid):
    sender = ''
    subject = ''
    payload = ''
    attachments = ''
    filenames = []

    # Fetch unread emails
    result, data = mail.uid('fetch', uid, '(RFC822)') # By fetching the message following RFC 822, it becomes automatically read
    if result != 'OK':
        return result

    # Parse the message
    message = email.message_from_string(data[0][1].decode(encoding='utf-8', errors='ignore'))

    # Save some header information Feature: recognize replies and Cc
    temp_sender = decode_header(message['from'])
    sender = email.utils.parseaddr(str(temp_sender[0][0]))[0]
    # Sometimes email.utils doesn't work well...
    if sender == '':
        sender = temp_sender[0][0]
    # Not all message headers are encoded as bytes
    try:
        sender = sender.decode('utf-8')
        # NOTE: do not try to print sender or subject on the console, or
        # it will rise an error, although the message on Telegram is
        # good
    except AttributeError:
        pass

    subject = decode_header(message['subject'])
    subject = subject[0][0]
    # Not all message headers are encoded as bytes
    try:
        subject = subject.decode('utf-8')
    except AttributeError:
        pass

    # Decode and save only the plain text body NOTE: we do not use the
    # method get_body; we use walk instead, because we think it is safer
    if not message.is_multipart():
        charset = message.get_content_charset()
        payload = message.get_payload(decode=True).decode(encoding = charset, errors = 'ignore')
    else:
        for part in message.walk():
            charset = part.get_content_charset()
            if part.get_content_type() == 'text/plain':
                payload += part.get_payload(decode=True).decode(encoding = charset, errors = 'ignore') + '\n'
            # If there is an attachment, inform the user
            if not part.get_content_maintype() in ['text', 'multipart', 'message']:
                filename = part.get_filename()
                attachments += filename + ': ' + part.get_content_type() + '\n'
                if bool(filename):
                    fp = open('/home/fmarotta/raspbotpi/attachments/{}'.format(filename), 'wb')
                    fp.write(part.get_payload(decode=True))
                    fp.close()
                    filenames.insert(0, filename)

    # Inform the user if there is no textual payload
    if payload == '':
        payload = 'No textual payload'

    # Parse the body for any eventual HTML and return only the text
    soup = BeautifulSoup(payload, 'html5lib')
    payload = soup.get_text()

    # Replace `<' and `>' characters, because they confuse the Telegram
    # API The replacement characters are, respectively, the
    # less-than-or-equal-to and the greater-than-or-equal-to signs
    payload = payload.replace('<', '≤')
    payload = payload.replace('>', '≥')

    # Instead of letting this field blank, tell 'None'
    if attachments == '':
        attachments = 'None'

    return result, sender, subject, payload, attachments, filenames


def fetch_email(account):
    msg = []

    result, mail = imap_connect(account)
    if result != 'OK':
        bot.sendMessage(my_id, 'Error while connecting to {}: {}'.format(account.username, mail))

    # Select the folders to search for messages
    for folder in account.folders:
        result, uids = search_email(mail, folder)
        if result != 'OK':
            bot.sendMessage(my_id, 'Error while searching ' + folder + ' of ' + account.username + ': ' + result)
            return
        if uids[0] == '':
            # There is nothing to read here
            continue

        # Parse each message in the folder
        uid_list = uids[0].split()
        for uid in uid_list:
            result, sender, subject, payload, attachments, filenames = parse_email(mail, uid)
            if result != 'OK':
                bot.sendMessage(my_id, 'Error while searching ' + folder + ' of ' + account.username + ': ' + result)
                return

            # Keyboard
            if (attachments != 'None'):
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='Download Attachments', callback_data='da:{}:{}:{}'.format(account.username, folder, uid))]
                ])
            else:
                keyboard = None

            # Messages to send if there are emails
            msg.insert(0, ['<b>You\'ve got a new e-mail!</b>\n<pre>From: {}\nTo: {}\nSubject: {}\nAttachments: {}\n</pre>\n{}'.format(sender, account.username, subject, attachments, payload), keyboard, filenames])

    # Close the connection and logout
    mail.close()
    mail.logout()

    return list(reversed(msg))


for account in accounts:
    msg = fetch_email(account)
    for mex in msg:
        text = mex[0]
        keyboard = mex[1]
        filenames = mex[2]
        try:
            bot.sendMessage(my_id, text, 'HTML')
        except telepot.exception.TelegramError as err:
            if (err.description == 'Bad Request: message is too long'):
                # Split the long message in chunks (max lenght for the
                # API is 4096 bytes)
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)] # I brutally copied this line from http://stackoverflow.com/questions/9475241/split-python-string-every-nth-character
                for chunk in chunks:
                    bot.sendMessage(my_id, chunk, 'HTML')
            else:
                bot.sendMessage(my_id, 'You\'ve got new mails to {}, but I could\'t send them because of a Telegram error: {}'.format(account.username, err))

        for filename in filenames:
            with open('/home/fmarotta/raspbotpi/attachments/{}'.format(filename), 'rb') as attachment:
                bot.sendDocument(my_id, attachment, caption = filename)
            os.remove('/home/fmarotta/raspbotpi/attachments/{}'.format(filename))
