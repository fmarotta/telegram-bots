# Telegram-Bots
A set of bots to integrate Raspberry Pi management, email reading and RSS feed updates within Telegram.

## Description
Telegram bots are special accounts that are not associated with any person; indeed, they are applications [1]. I have implemented
three bots for personal use: one spawns a pseudoterminal from the computer where the bot is hosted, and allows me to send the bot
messages that are interpreted as shell commands; one regularly connects to my IMAP accounts and informs me when I have a new
email, also sending me its content; and one sends me the updates of the RSS feeds I "subscribed". As I said, these project is for
personal use, therefore I do not provide any instruction on how to use the code; however, if you are interested, do not hesitate
and contact me.

### pseudoterminal
This guy here is written in Node.js, and it is inspired by https://github.com/jmendeth/node-botgram/tree/master/examples/shell.
Every message I send it is executed in a pseudoterminal, then the output is sent back to me. Moreover, it has some nice commands
built in such as "/download", which allows me to fetch a file from the bot's host.  
The reason why I developed this is to have access to the bot's host (which is a Raspberry Pi) from anywhere without installing
additional software; in particular I can use the Telegram App from my smartphone or Telegram Web from any device!

### mail
This bot, like the next one, is written in python. Basically, it connects to my IMAP accounts, looks for unread emails, and if
there is any, starts parsing it. This is not a trivial task, because many modern emails use the MIME standard [2], which allows
to send contents other than 7-bit ASCII plain texts, but, on the other hand, makes more difficult to print an email in an
environment like Telegram, where only plain text is supported (with some basic markdown). Thus, the program extrapolates only
the text part of the email before sending it to me on Telegram. So far, I have tested it only with Gmail accounts.  
I developed this bot mostly because I was tired of compulsively looking for new emails (for example for my exam results...). Now
I know that if I have a new email, my bot will tell me.

NOTE: if you have a google account, you have to allow access to less 
secure apps in order for the program to work.

### rss
I also was tired of compulsively looking for updates in some RSS feeds. This last (so far) bot connects to an RSS URL, and if there is a new post since the last time the program has checked, it sends me the content of the post.

-----

Note that I have spoken of the three programs like they were individual bots. Actually, in my setup they all are associated with one single bot, but both the configurations are possible. This increases modularity.

That's pretty much it, except for one thing. To make these three tasks (sending commands to a remote server, reading emails and
RSS feeds) there is no need for a Telegram bot. However, I find it fascinating that now these simple things are integrated in my
Telegram App and I can manage them from one single place. Besides, while writing these programs I have learned a lot of new things.

## Disclaimer
I do not consider myself a programmer. I posted the code here hoping that it is useful to somebody. Use it at your own risk ;)  
For further information, suggestions or critics, contact me at the email address in my profile.

[1] https://core.telegram.org/bots  
[2] https://en.wikipedia.org/wiki/MIME
