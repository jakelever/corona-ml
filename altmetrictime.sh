#!/bin/bash
#
#SBATCH --job-name=coronaMiniupdate
#
#SBATCH --time=1:00:00
#SBATCH --mem=8G
#SBATCH -p rbaltman

set -ex

date

#base="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
base=/home/groups/rbaltman/jlever/corona-ml

cd $base

if [ -d .coronalock ]; then
	echo "Skipping. Full build is in progress"
	exit 0
fi

aws_login=`cat $base/aws_login.txt`

cd $base/altmetric
python getAltmetricData.py --apiKeyFile ../altmetricApiKey.json --documents ../pipeline/data/coronacentral.json --popularOrRecent --prevData ../pipeline/data/altmetric.json --outData recent_altmetric.json

db=$base/database/aws.json

python ../database/loadAltmetricData.py --db $db --json recent_altmetric.json

cd $base
#ssh -i aws_time.pem $aws_login ". ~/.bash_profile && cd corona-web && npm run build && sudo pm2 restart next"
ssh -i aws_time.pem $aws_login ". ~/.bash_profile && cd corona-web && sh redeploy.sh"

python pokeWebsite.py

date

