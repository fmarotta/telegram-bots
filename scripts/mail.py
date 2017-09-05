#!/usr/bin/python3

"""

This program connects to an imap account, fetches the unread emails
and sends the plain text parts to a Telegram user through a bot.

"""

import telepot
import ssl
import imaplib
import email
import sys
import time
from email.header import decode_header
from bs4 import BeautifulSoup # Install package ``beautifulsoup4'' via pip.

if len(sys.argv) != 3:
    print('Usage: python mail.py <bot\'s token> <your Telegram ID>')
    sys.exit()

# Initialize the bot
token = sys.argv[1]
my_id = sys.argv[2]
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
with open('../config/mail_accounts') as mail_accounts:
    lines = mail_accounts.readlines()
    for imap_params in lines:
        imap_params = imap_params.rstrip("\n")
        accounts.append(ImapAccount(imap_params.split("\t")))

# The function which fetches the messages
def fetch_email(account):
    msg = []
    # Create a ssl context for the connection to the imap server
    try:
        context = ssl.create_default_context()
        print(context)
    except ssl.SSLError as err:
        print(err);

    # Connect to the server
    try:
        mail = imaplib.IMAP4_SSL(host=account.host, port=account.port, ssl_context=context)
    except IMAP4.error as err:
        print('error while connecting to the server for {}.\nError: {}'.format(account, err));
        return

    # Login to the specified account
    result, address = mail.login(account.username, account.password)
    if result != 'OK':
        bot.sendMessage(my_id, 'Error while logging in to ' + account.username + ': ' + result)
        return

    # Select the folders to search for messages
    for folder in account.folders:
        # Select the specified folder
        result, n_mails = mail.select(folder)
        if result != 'OK':
            bot.sendMessage(my_id, 'Error while selecting ' + folder + ' from ' + account.username + ': ' + result)
            return

        # Search for unread emails
        result, uids = mail.uid('search', None, '(UNSEEN)')
        if result != 'OK':
            bot.sendMessage(my_id, 'Error while searching new e-mails in ' + account.username + ': ' + result)
            return
        if uids[0] == '':
            # There is nothing to read here
            continue

        uid_list = uids[0].split()
        for uid in uid_list:
            # Variables definition
            payload = ''
            attachments = ''
            # Fetch the unread emails
            result, data = mail.uid('fetch', uid, '(RFC822)') # By fetching the message following RFC 822, it becomes automatically read
            if result != 'OK':
                bot.sendMessage(my_id, 'Error while fetching new e-mails from ' + account.username + '\n: ' + result)
                return

            # Parse the message
            message = email.message_from_string(data[0][1].decode(encoding='utf-8', errors='ignore'))

            # Save some header information
            # Feature: recognize replies and Cc
            temp_sender = decode_header(message['from'])
            sender = email.utils.parseaddr(str(temp_sender[0][0]))[0]
            # Sometimes email.utils doesn't work well...
            if sender == '':
                sender = temp_sender[0][0]
                # Not all message headers are encoded as bytes
                try:
                    sender = sender.decode('utf-8')
                    # NOTE: do not try to print sender or subject
                    # on the console, or it will rise an error,
                    # although the message on Telegram is good
                except AttributeError:
                    pass
                    
            subject = decode_header(message['subject'])
            subject = subject[0][0]
            # Not all message headers are encoded as bytes
            try:
                subject = subject.decode('utf-8')
            except AttributeError:
                pass

            # Decode and save only the plain text body
            # NOTE: we do not use the method get_body; we use
            # walk instead, because we think it is safer
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
                        attachments += part.get_content_type() + '\n'

            # Inform the user if there is no textual payload
            if payload == '':
                payload = 'No textual payload'

            # Parse the body for any eventual HTML and return only the text
            soup = BeautifulSoup(payload, 'html5lib')
            payload = soup.get_text()

            # Replace `<' and `>' characters, because they confuse the
            # Telegram API
            # The replacement characters are, respectively, the
            # less-than-or-equal-to and the greater-than-or-equal-to signs
            payload = payload.replace('<', '≤')
            payload = payload.replace('>', '≥')

            # Instead of letting this field blank, tell 'None'
            if attachments == '':
                attachments = 'None'

            # Messages to send if there are emails
            msg.insert(0, '<b>You\'ve got a new e-mail!</b>\n<pre>From: {}\nTo: {}\nSubject: {}\nAttachments: {}\n</pre>\n{}'.format(sender, account.username, subject, attachments, payload))

    # Close the connection and logout
    mail.close()
    mail.logout()

    return msg

while 1:
    for account in accounts:
        msg = fetch_email(account)
        for mex in msg:
            try:
                bot.sendMessage(my_id, mex, 'HTML')
            except telepot.exception.TelegramError as err:
                if (err.description == 'Bad Request: message is too long'):
                    # Split the long message in chunks (max lenght for the API
                    # is 4096 bytes)
                    chunks = [mex[i:i+4000] for i in range(0, len(mex), 4000)] # I brutally copied this line from http://stackoverflow.com/questions/9475241/split-python-string-every-nth-character
                    for chunk in chunks:
                        bot.sendMessage(my_id, chunk, 'HTML')
                else:
                    bot.sendMessage(my_id, 'You\'ve got new mails to {}, but I could\'t send them because of a Telegram error: {}'.format(account.username, err))
    # Execute this every 14 minutes
    time.sleep(14 * 60)

