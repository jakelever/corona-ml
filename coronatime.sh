#!/bin/bash
#
#SBATCH --job-name=coronaBigUpdate
#
#SBATCH --time=12:00:00
#SBATCH --mem=32G
#SBATCH -p rbaltman

set -ex

date

if [ -n $SLURM_JOB_ID ] ; then
	base=$(scontrol show job $SLURM_JOBID | awk -F= '/Command=/{print $2}' | xargs dirname)
else
	base=$(dirname "$0")
fi

#mkdir .coronalock

aws_login=`cat $base/aws_login.txt`

origdate=NONE
if [ -f $base/pipeline/data/coronacentral.json ]; then
	origdate=`stat -c %y $base/pipeline/data/coronacentral.json`
fi

cd $base/data
sh run_update.sh

cd $base/pipeline
snakemake --cores 1 data/coronacentral.json.gz

newdate=`stat -c %y $base/pipeline/data/coronacentral.json`

if [[ "$origdate" == "$newdate" ]] && [ -f $base/pipeline/data/coronacentral.json ] && [ -f $base/pipeline/data/altmetric.json ]; then
	echo "NO update so running quick Altmetric update..."
	
	cd $base/altmetric
	python getAltmetricData.py --apiKeyFile ../altmetricApiKey.json --documents ../pipeline/data/coronacentral.json --popularOrRecent --prevData ../pipeline/data/altmetric.json --outData recent_altmetric.json

	db=$base/database/aws.json
	python ../database/loadAltmetricData.py --db $db --json recent_altmetric.json

else
	echo "New data so fetching full altmetric and refreshing full DB..."

	cd $base/pipeline
	snakemake --cores 1 data/altmetric.json

	cd $base/database
	sh reload_db.sh
fi

cd $base
#ssh -i aws_time.pem $aws_login ". ~/.bash_profile && cd corona-web && npm run build && sudo pm2 restart next"
ssh -i aws_time.pem $aws_login ". ~/.bash_profile && cd corona-web && sh redeploy.sh"

sleep 10

python pokeWebsite.py

#rmdir .coronalock

cd $base/twitter
sh dotweet.sh

cd $base
last_upload=`cat last_upload.log`
this_week=`date +"week %U of %Y"`
if [[ "$last_upload" != "$this_week" ]]; then
	echo "Publishing to Zenodo..."
	bigzenodo --submission submission.json --accessTokenFile ~/zenodo_token.txt --publish
	echo "$this_week" > last_upload.log
fi

date

