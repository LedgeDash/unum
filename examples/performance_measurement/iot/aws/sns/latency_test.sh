#!/usr/bin/env bash

DURATION=3 # minutes
INTERVAL=1 # seconds
ITERATION=$( bc <<< "1 / $INTERVAL * $DURATION * 60" )

for (( i=0; i<$ITERATION; i++ ))
do
    echo -ne "$i out of $ITERATION invocations\r"
    make test-app > /dev/null
    sleep $INTERVAL
done
