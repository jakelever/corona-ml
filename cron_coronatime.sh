#!/bin/bash
#SBATCH --job-name=cronCoronaCentral
#SBATCH --begin=now+4hours
#SBATCH --dependency=singleton
#SBATCH --time=12:00:00
#SBATCH --mail-type=FAIL
#SBATCH --mem=64G
#SBATCH -p rbaltman
#SBATCH --gpus 1
set -ex

## Resubmit the job for the next execution
sbatch $0

## Insert the command to run below. Here, we're just storing the date in a
## cron.log file
sh /home/groups/rbaltman/jlever/corona-ml/coronatime.sh

