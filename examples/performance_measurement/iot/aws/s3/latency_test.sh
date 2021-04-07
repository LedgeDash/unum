#!/usr/bin/env bash

DURATION=3 # minutes
INTERVAL=4 # seconds
ITERATION=$( bc <<< "60 / $INTERVAL * $DURATION" )

echo $ITERATION

for (( i=0; i<$ITERATION; i++ ))
do
    echo -ne "$i out of $ITERATION invocations\r"
    make test-app > /dev/null
    sleep $INTERVAL
done
