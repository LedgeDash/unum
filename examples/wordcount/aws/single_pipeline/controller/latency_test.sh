#!/usr/bin/env bash

DURATION=1 # minutes
INTERVAL=0.5 # seconds
ITERATION=$( bc <<< "60 / $INTERVAL * $DURATION" )

for (( i=0; i<$ITERATION; i++ ))
do
    echo -ne "$i out of $ITERATION invocations\r"
    make test-app > /dev/null
    sleep $INTERVAL
done
