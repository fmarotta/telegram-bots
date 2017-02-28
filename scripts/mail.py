"""

This program connects to an imap account, fetches the unread emails
and sends the plain text parts to a Telegram user through a bot.

"""

# I am so lazy that I hard coded a bunch of things... sorry

import telepot
import ssl
import imaplib
import email
import time
from email.header import decode_header
from bs4 import BeautifulSoup

# Initialize the bot
# TODO: read my id and the bot token from a file,
# or from the command line arguments
bot = telepot.Bot(#INSERT TOKEN#)
my_id = #INSERT ID#

# Define the mail account class
class ImapAccount:
    host = ''
    port = 993
    username = ''
    password = ''
    folders = ['inbox']

# Define the accounts as an array of objects
# TODO: read the account info from a file for easier modification
# or better yet let the bot ask the user
federicomarotta96ATgmailDOTcom = ImapAccount()
federicomarotta96ATgmailDOTcom.host = #INSERT MAIL SERVER#
federicomarotta96ATgmailDOTcom.username = #INSERT USERNAME#
federicomarotta96ATgmailDOTcom.password = #INSERT PASSWORD#

accounts = [federicomarotta96ATgmailDOTcom]

# The function which fetches the messages
def fetch_email(account):
    # Variables definition
    payload = ''
    attachments = ''
    msg = []
    # Create a ssl context for the connection to the imap server
    context = ssl.create_default_context()
    # Connect to the server
    mail = imaplib.IMAP4_SSL(host=account.host, port=account.port, ssl_context=context)

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
            # Fetch the unread emails
            result, data = mail.uid('fetch', uid, '(RFC822)') # By fetching the whole RFC 822 message, it becomes automatically read
            if result != 'OK':
                bot.sendMessage(my_id, 'Error while fetching new e-mails from ' + account.username + '\n: ' + result)
                return

            # Parse the message
            message = email.message_from_string(data[0][1].decode(encoding='utf-8'))

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
            # NOTE: we do not use the method get_body(); we use
            # walk() instead, because we think it is safer
            if not message.is_multipart():
                payload = message.get_payload(decode=True).decode('utf-8')
            else:
                for part in message.walk():
                    charset = part.get_content_charset()
                    if part.get_content_type() == 'text/plain':
                        payload += part.get_payload(decode=True).decode(charset) + '\n'
                    # If there is an attachment, inform the user
                    if not part.get_content_maintype() in ['text', 'multipart', 'message']:
                        attachments += part.get_content_type() + '\n'

            # Inform the user if there is no textual payload
            if payload == '':
                payload = 'No textual payload'

            # Parse the body for any eventual HTML and return only the text
            soup = BeautifulSoup(payload, 'html5lib')
            payload = soup.get_text()
                
            # Instead of letting this field blank, tell 'None'
            if attachments == '':
                attachments = 'None'

            # Messages to send if there are emails
            msg.insert(0, '*You\'ve got a new e-mail!*\n```\nFrom: {}\nTo: {}\nSubject: {}\nAttachments: {}```\n\n{}'.format(sender, account.username, subject, attachments, payload))

    # Close the connection and logout
    mail.close()
    mail.logout()

    return msg

while 1:
    for account in accounts:
        msg = fetch_email(account)
        for mex in msg:
            try:
                bot.sendMessage(my_id, mex, 'Markdown')
            except telepot.exception.TelegramError:
                bot.sendMessage(my_id, 'You\'ve got new mails to {}, but I could\'t send them because of a Telegram error'.format(account.username))
    # Execute this every 14 minutes
    time.sleep(14 * 60)

