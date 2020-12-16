#!/bin/bash
#
#SBATCH --job-name=coronaBigUpdate
#
#SBATCH --time=12:00:00
#SBATCH --mem=32G
#SBATCH -p rbaltman

set -ex

date

#base="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
base=/home/groups/rbaltman/jlever/corona-ml

aws_login=`cat aws_login.txt`

mkdir .coronalock

cd $base/data
sh run_update.sh

cd $base/pipeline
snakemake --cores 1 data/autoannotations.json data/altmetric.json

cd $base/database
sh reload_db.sh

cd $base
#ssh -i aws_time.pem $aws_login ". ~/.bash_profile && cd corona-web && npm run build && sudo pm2 restart next"
ssh -i aws_time.pem $aws_login ". ~/.bash_profile && cd corona-web && sh redeploy.sh"

python pokeWebsite.py

rmdir .coronalock

date

