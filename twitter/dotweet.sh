#!/bin/bash
set -ex

last_tweet=`cat last_tweet.log`
today=`date +"%m-%d-%y"`
if [[ "$last_tweet" == "$today" ]]; then
	echo "Already tweeted today. No more!"
	exit 0
fi

latestAltmetric=`ls -tr ../altmetric/recent_altmetric.json ../pipeline/data/altmetric.json | tail -n 1`

python tweet.py --documents ../pipeline/data/coronacentral.json --altmetric $latestAltmetric --twitterApiKey twitterApiKey.json

echo $today > last_tweet.log

