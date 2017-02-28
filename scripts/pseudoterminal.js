/*
 *  This program implements a bot such that every message the user
 *  sends it is interpreted as a shell command and is executed in a
 *  pseudoterminal.
 */
 
// Forgive my laziness but I hard coded my Telegram ID and the bot's token
// If you want to use this code, insert your parameters where indicated

const Telegraf = require('/usr/lib/node_modules/telegraf')
const Pty = require('/usr/lib/node_modules/pty')
const Fs = require('fs')
const Https = require('https')

const my_id = // Insert telegram user ID here
const token = // Insert token here
const bot = new Telegraf(token)

var pty = 0

bot.on(['message', 'edited_message', 'callback_query', 'inline_query', 'chosen_inline_result', 'channel_post', 'edited_channel_post'], (ctx, next) => {

    // Define some useful variables for siplicity's sake
    username = ctx.message.from.username
    id = ctx.message.from.id
    text = ctx.message.text

    // Check the identity of the sender
    if (id != my_id) {

        // Send a message to the sender
        ctx.reply('Sorry, you are not allowed to use this bot.\n' +
            'This incident will be reported.'
        )

        // And a message to me
        ctx.telegram.sendMessage(my_id, 'Bot violation\n' + 
            'User "' + username + '" ' +
            '(' + id + ')\n' +
            'Wrote "' + text + '"'
        )

        return

    }
        
    next()

})

bot.command('kill', (ctx, next) => {

    if (pty == 0) {

        ctx.reply('No process is running')

        return

    }

    var pid = pty.pid
    var signal = ctx.message.text.split(' ')[1]
    var signals = ['SIGHUP', 'SIGINT', 'SIGQUIT', 'SIGILL',
        'SIGTRAP', 'SIGABRT', 'SIGBUS', 'SIGFPE', 'SIGKILL',
        'SIGUSR1', 'SIGSEGV', 'SIGUSR2', 'SIGPIPE', 'SIGALRM',
        'SIGTERM', 'SIGSTKFLT', 'SIGCHLD', 'SIGCONT',
        'SIGSTOP', 'SIGTSTP', 'SIGTTIN', 'SIGTTOU', 'SIGURG',
        'SIGXCPU', 'SIGXFSZ', 'SIGVTALRM', 'SIGPROF',
        'SIGWINCH', 'SIGIO', 'SIGPWR', 'SIGSYS', 'SIGRTMIN']

    if (signals.indexOf(signal) == -1) {

        if (signal == null) {

            signal = 'SIGTERM'

        }else {

            ctx.reply('Send a valid signal')

        }
            
    }

    try {

        process.kill(pid, signal)

    }catch (err) {

        ctx.reply('Couldn\'t send signal, ' + err)

        return

    }

    return

})

bot.command('download', (ctx, next) => {

    var args = ctx.message.text.split(' ')
    args.shift()

    if (args == '') {

        ctx.reply('Tell me which files you want to download')

        return

    }

    args.forEach(function(arg) {

        var filename = arg.split('/').slice(-1)[0]
        var extension = filename.split('.').slice(-1)[0].toLowerCase()

        var audioExtensions = ['wav', 'mp3', 'flac', 'midi', 'au', 'wma']
        var photoExtensions = ['jpeg', 'jpg', 'tiff', 'tif', 'gif', 'bmp',
            'png', 'webp', 'bpg', 'cgm', 'svg']
        var videoExtensions = ['webm', 'mkv', 'flv', 'avi', 'wmv', 'mov',
            'qt', 'mp4', 'mpg', 'mpeg']

        try {

            if (audioExtensions.indexOf(extension) > -1) {

                ctx.replyWithAudio(
                    {source: Fs.createReadStream(arg)},
                    {caption: filename}
                )

            }else if (photoExtensions.indexOf(extension) > -1) {

                ctx.replyWithPhoto(
                    {source: Fs.createReadStream(arg)},
                    {caption: filename}
                )

            }else if (videoExtensions.indexOf(extension) > -1) {

                ctx.replyWithVideo(
                    {source: Fs.createReadStream(arg)},
                    {caption: filename}
                )

            }else {

                ctx.replyWithDocument(
                    {source: Fs.createReadStream(arg)},
                    {caption: filename}
                )

            }

            ctx.reply('File sent')

        }catch (err) {

            ctx.reply(err)
            
            return

        }

    })

    return

})

bot.on('text', (ctx, next) => {

    // Define some useful variables for siplicity's sake
    text = ctx.message.text

    // Execute the command received
    // if another command is not already running
    if (!pty) {

        // Exception: cd command can't be handled by the pty
        if (text.match(/^cd/)) {

            var dir = text.split(' ')[1]

            try {

                process.chdir(dir)

            }catch (err) {

                ctx.reply(err)
            
                return

            }

            ctx.reply('Done')

            return

        }

        // Spawn a new pty
        pty = Pty.spawn('/bin/sh', ['-c', text], {
            name: 'dumb',
            cols: 40,
            rows: 20,
            cwd: process.cwd() || process.env.HOME,
            env: getEnv(),
        })
    
        // Process the output
        pty.on('data', function(data) {

            // FIXME: add a promise rejection handler
            ctx.reply(data)

        })

        // Process the exit code
        pty.on('exit', function(code, signal) {
    
            pty = 0

            if (!signal && !code) {

                ctx.reply('Done')

            }else {

                if (signal) {

                    ctx.reply('Killed by signal ' + signal)

                }else {

                    ctx.reply('Exited with ' + code)

                }

            }

        })

    }else {
    
        // Send data to the pty
        pty.write(text)

    }

    return
    
}) 


// Start listening to messages
bot.startPolling()


// Functions
function getEnv() {

    // Adapted from the source code of the module pty.js
    var env = {}

    Object.keys(process.env).forEach(function (key) {
      env[key] = process.env[key]
    })

    // Make sure we didn't start our
    // server from inside tmux.
    delete env.TMUX
    delete env.TMUX_PANE
  
    // Make sure we didn't start
    // our server from inside screen.
    // http://web.mit.edu/gnu/doc/html/screen_20.html
    delete env.STY
    delete env.WINDOW
  
    // Delete some variables that
    // might confuse our terminal.
    delete env.WINDOWID
    delete env.TERMCAP
    delete env.COLUMNS
    delete env.LINES
  
    // Set $TERM to screen. This disables multiplexers
    // that have login hooks, such as byobu.
    env.TERM = "screen"
  
    return env

}

