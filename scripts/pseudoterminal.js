#!/usr/bin/node

/*
 *  This program implements a pseudoterminal one can interact with through
 *  a Telegram bot.
 */

// Import the modules
// NOTE: pty module requires python2, make and gcc for installation (then
// you can uninstall at least python2). It also requires the node module nan. Last time I did this:
// 1) As root (not sudo) npm install node-pty (without -g)
// 2) Move the modules in /usr/lib/node_modules
const Telegraf = require('/usr/lib/node_modules/telegraf')
const Pty = require('/usr/lib/node_modules/node-pty')
const Fs = require('fs')
const Https = require('https')

// Check if the number of arguments is right
if (process.argv.length != 4) {
    console.log('Pass me the bot\'s token and your Telegram ID as arguments')
    process.exit()
}

// Start the bot
const token = process.argv[2]
const my_id = parseInt(process.argv[3])
const bot = new Telegraf(token)

// Set the home variable
const home = '/home/fmarotta/'

// Initialize the pty variable to take a track of wether a command is
// running or not
var pty = 0

// Check the user's identity
bot.on(['message', 'edited_message', 'inline_query', 'channel_post', 'edited_channel_post'], (ctx, next) => {

    // Define some useful variables for simplicity's sake
    username = ctx.message.from.username
    id = ctx.message.from.id
    text = ctx.message.text

    if (id != my_id) {

        // Send a message to the sender
        ctx.reply('Sorry, you are not allowed to use this bot.\n' +
            'This incident will be reported.'
        )

        // And a message to the bot's master
        ctx.telegram.sendMessage(my_id, 'Bot violation\n' + 
            'User "' + username + '" ' +
            '(' + id + ')\n' +
            'Wrote "' + text + '"'
        )

        return

    }
        
    // Call next middleware
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

    // NOTE: do not worry about shell special characters: do not escape them in the message.
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

        }catch (err) {

            ctx.reply(err)

            return

        }

        ctx.reply('File in the hole!')

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

            if (dir == undefined || dir == '~') {

                // NOTE: executing the script with systemd doesn't set a
                // process.env.HOME variable.
                // dir = process.env.HOME
                dir = home

            }

            try {

                process.chdir(dir)

            }catch (err) {

                ctx.reply("Unable to change directory: " + err)
            
                return

            }

            ctx.reply('Done')

            return

        }

        // Running bash causes the program to break very badly
        if (text.match(/^bash/)) {

            ctx.reply('Cannot start another bash process')

            return

        }

        // Spawn a new pty
        // Available pty types:
        // amiga
        // beos-ansi
        // ansi
        // pcansi
        // win32
        // vt320
        // vt52
        // xterm
        // iris-ansi
        // debug
        // dumb
        pty = Pty.spawn('/bin/bash', ['-c', text], {
            //name: 'xterm', // If you want to use xterm, you have to manage control sequences... see http://wiki.bash-hackers.org/scripting/terminalcodes
            //name: 'vt52', // This tty uses 24 characters for colors. Nice!
            name: 'dumb',
            cols: 80,
            rows: 100,
            cwd: process.cwd() || home, // process.cwd() is better because then you can use relative paths
            env: getEnv(),
        })
    
        // Process the output
        // FIXME: sometimes messages are fragmented and sent in the wrong order.
        // Maybe add some kind of buffer? However, for interactive commands that
        // would be a problem.
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

    // Set the home directory.
    env.HOME = home
  
    return env

}
