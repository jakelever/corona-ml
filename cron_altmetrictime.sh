#!/bin/bash
#SBATCH --job-name=cronCoronaCentralAltmetric
#SBATCH --begin=now+1hour
#SBATCH --dependency=singleton
#SBATCH --time=00:55:00
#SBATCH --mail-type=FAIL
#SBATCH --mem=8G
#SBATCH -p rbaltman
set -ex

## Insert the command to run below. Here, we're just storing the date in a
## cron.log file
sh /home/groups/rbaltman/jlever/corona-ml/altmetrictime.sh

## Resubmit the job for the next execution
sbatch $0

