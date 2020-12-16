#!/bin/bash
set -ex

last_tweet=`cat last_tweet.log`
today=`date +"%m-%d-%y"`
if [[ "$last_tweet" == "$today" ]]; then
	echo "Already tweeted today. No more!"
	exit 0
fi
echo $today > last_tweet.log

latestAltmetric=`ls -tr ../altmetric/recent_altmetric.json ../pipeline/data/altmetric.json | tail -n 1`

python tweet.py --documents ../pipeline/data/alldocuments.final.json --altmetric $latestAltmetric --twitterApiKey twitterApiKey.json

