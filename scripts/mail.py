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
import smtplib
import email
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import sys
import os
import time

sys.path.insert(0, "/home/fmarotta/raspbotpi/lib/python3.7")
import telepot
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from bs4 import BeautifulSoup # Or install package beautifulsoup4 via pip

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
    def __init__(self, params):
        self.imap_host = params[0]
        self.imap_port = params[1]
        self.smtp_host = params[2]
        self.smtp_port = params[3]
        self.username = params[4]
        self.password = params[5]
        self.folders = params[6].split(",")

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
        mail = imaplib.IMAP4_SSL(host=account.imap_host, 
                port=account.imap_port, ssl_context=context)
    except IMAP4.error as err:
        return 1, err

    # Login to the specified account
    result, address = mail.login(account.username, account.password)
    if result != 'OK':
        return 1, result

    return 'OK', mail

def smtp_connect(account):
    # Create a ssl context for the connection to the imap server
    try:
        context = ssl.create_default_context()
    except ssl.SSLError as err:
        return 1, err

    # Connect to the server
    try:
        mail = smtplib.SMTP_SSL(host=account.smtp_host, 
                port=account.smtp_port, context=context)
        mail.ehlo()
    except Exception as err:
        try:
            mail = smtplib.SMTP(host=account.smtp_host, 
                    port=account.smtp_port)
            mail.starttls()
            mail.ehlo()
        except Exception as err:
            return 1, err

    # Login to the specified account
    try:
        result, address = mail.login(account.username, account.password)
    except Exception as err:
        return 1, err

    return 'OK', mail

def parse_email(mail, uid):
    sender = ''
    receipient = ''
    cc = ''
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

    # Save some header information
    sender = decode_header(message['from'])[0][0].replace('<', 
            '≤').replace('>', '≥')
    receipient = decode_header(message['to'])[0][0].replace('<', 
            '≤').replace('>', '≥').replace('\n', ' ')
    try:
        cc = decode_header(message['cc'])[0][0].replace('<', 
                '≤').replace('>', '≥').replace('\n', ' ')
    except TypeError:
        cc = 'Nobody'
    subject = decode_header(message['subject'])[0][0].replace('<', 
            '≤').replace('>', '≥')
    message_id = decode_header(message['message-id'])[0][0].replace('<', 
            '≤').replace('>', '≥')

    #temp_sender = decode_header(message['from'])
    #sender = email.utils.parseaddr(str(temp_sender[0][0]))[0]
    # Sometimes email.utils doesn't work well...
    #if sender == '':
        #sender = temp_sender[0][0]

    # Not all message headers are encoded as bytes
    try:
        sender = sender.decode('utf-8')
        # NOTE: do not try to print sender or subject on the console, or
        # it will rise an error, although the message on Telegram is
        # good
    except AttributeError:
        pass

    try:
        receipient = receipient.decode('utf-8')
    except AttributeError:
        pass

    try:
        cc = cc.decode('utf-8')
    except AttributeError:
        pass

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
                attachments += '"' + filename + '"' + ' (' + part.get_content_type() + '), '
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
    # Remove trailing comma
    attachments = attachments.rstrip(' ,')

    return result, sender, receipient, cc, subject, message_id, payload, attachments, filenames


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
            result, sender, receipient, cc, subject, message_id, payload, attachments, filenames = parse_email(mail, uid)
            if result != 'OK':
                bot.sendMessage(my_id, 'Error while searching ' + folder + ' of ' + account.username + ': ' + result)
                return

            # Keyboard
            #if (attachments != 'None'):
                #keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    #[InlineKeyboardButton(text='Download Attachments', 
                    #callback_data='da:{}:{}:{}'.format(account.username, 
                    #folder, uid))]
                #])
            #else:
                #keyboard = None
            keyboard = None

            # Messages to send if there are emails
            msg.insert(0, ['<b>You\'ve got a new \
e-mail!</b>\n<pre>Delivered to: {}\nFrom: {}\nTo: {}\nCc: \
{}\nSubject: {}\nID: {}\nAttachments: \
{}\n</pre>\n{}'.format(account.username, sender, receipient, cc, 
    subject, message_id, attachments, payload), keyboard, filenames])

    # Close the connection and logout
    mail.close()
    mail.logout()

    return list(reversed(msg))

if len(sys.argv) == 1:
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
                    # Split the long message in chunks (max lenght for 
                    # the API is 4096 bytes)
                    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)] # I brutally copied this line from http://stackoverflow.com/questions/9475241/split-python-string-every-nth-character
                    for chunk in chunks:
                        bot.sendMessage(my_id, chunk, 'HTML')
                else:
                    bot.sendMessage(my_id, 'You\'ve got new mails to {}, but I could\'t send them because of a Telegram error: {}'.format(account.username, err))

            for filename in filenames:
                with open('/home/fmarotta/raspbotpi/attachments/{}'.format(filename), 'rb') as attachment:
                    bot.sendDocument(my_id, attachment, caption = filename)
                os.remove('/home/fmarotta/raspbotpi/attachments/{}'.format(filename))

elif len(sys.argv) == 2:
    mail_string = json.loads(sys.argv[1])
    mail_string["body"] += "\n\nSent from raspi."

    msg = MIMEMultipart("mixed")
    msg["from"] = mail_string["delivered_to"]
    msg["to"] = mail_string["from"]
    msg["cc"] = ", ".join(mail_string["receipients"])
    msg["subject"] = mail_string["subject"]
    msg["in-reply-to"] = mail_string["message_id"]
    msg["references"] = mail_string["message_id"]
    msg["message-ID"] = email.utils.make_msgid()
    body = MIMEMultipart("alternative")
    body.attach(MIMEText(mail_string["body"], "plain"))
    body.attach(MIMEText("<html>"+mail_string["body"]+"</html>", 
        "html"))
    msg.attach(body)

    # TODO: error checking if the email is not sent
    for account in accounts:
        if (account.username == mail_string["delivered_to"]):
            result, mail = smtp_connect(account)
            if (result != 'OK'):
                print(mail)
                sys.exit()
            receipients = [mail_string["from"]] + mail_string["receipients"]
            receipients = [x for x in receipients if x != 
                    account.username]
            receipients = list(set(receipients))
            mail.sendmail(account.username, receipients, msg.as_string())
            mail.quit()

            """ not necessary!
            # Since we send the message to us as well, we mark it as 
            # read
            result, mail = imap_connect(account)
            if (result != 'OK'):
                print(mail)
                sys.exit()
            result, n_mails = mail.select('Inbox')
            if (result != 'OK'):
                print(n_mails)
                sys.exit()
            result, id_mails = mail.search(None, '(UNSEEN)', '(FROM "' + account.username + '")')
            if (result != 'OK'):
                print(id_mails)
                sys.exit()
            for msg_id in id_mails[0].split():
                mail.store(msg_id, '+FLAGS', '\Seen')

            mail.close()
            mail.logout()
            """

    print("E-mail sent to " + ", ".join(receipients))
    sys.stdout.flush()
