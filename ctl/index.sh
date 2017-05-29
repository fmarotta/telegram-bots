#!/bin/bash

export BASEDIR='/home/fmarotta/raspbotpi'
TOKEN=`cut -f 1 ${BASEDIR}/config/params`
TELEGRAM_ID=`cut -f 2 ${BASEDIR}/config/params`

function begin {
    ${BASEDIR}/scripts/$1 $2 $3 &>> ${BASEDIR}/log/raspbotpi.log &
}

function term {
    PID=`ps -ux | grep $1 | grep -v grep | tr -s ' ' | cut -d ' ' -f 2`
    kill $PID
}

for script in pseudoterminal.js mail.py rss.py
do
    if [ $1 == 'start' ]
    then
        begin $script $TOKEN $TELEGRAM_ID
    elif [ $1 == 'stop' ]
    then
        term $script
    else
        echo -e "Error\n"
    fi
done

unset BASEDIR

exit

