#!/bin/bash
#
#SBATCH --job-name=coronaBigUpdate
#
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH -p rbaltman
#SBATCH --gpus 1

set -ex

date

#base="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
base=/home/groups/rbaltman/jlever/corona-ml

#mkdir .coronalock

aws_login=`cat $base/aws_login.txt`

origdate=NONE
if [ -f $base/pipeline/data/alldocuments.json ]; then
	origdate=`stat -c %y $base/pipeline/data/alldocuments.json`
fi

cd $base/data
sh run_update.sh

newdate=`stat -c %y $base/pipeline/data/alldocuments.json`

if [[ "$origdate" == "$newdate" ]] && [ -f $base/pipeline/data/coronacentral.json ] && [ -f $base/pipeline/data/altmetric.json ]; then
	echo "NO update so running quick Altmetric update..."
	
	cd $base/altmetric
	python getAltmetricData.py --apiKeyFile ../altmetricApiKey.json --documents ../pipeline/data/coronacentral.json --popularOrRecent --prevData ../pipeline/data/altmetric.json --outData recent_altmetric.json

	db=$base/database/aws.json
	python ../database/loadAltmetricData.py --db $db --json recent_altmetric.json

else
	echo "New data so running full pipeline..."

	cd $base/pipeline
	snakemake --cores 1 data/autoannotations.json data/altmetric.json data/coronacentral.json.gz

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

date

