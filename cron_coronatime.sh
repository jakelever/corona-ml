#!/bin/bash
#SBATCH --job-name=cronCoronaCentral
#SBATCH --begin=now+8hours
#SBATCH --dependency=singleton
#SBATCH --time=12:00:00
#SBATCH --mail-type=FAIL
#SBATCH --mem=16G
#SBATCH -p rbaltman
set -ex

## Resubmit the job for the next execution
sbatch $0

## Insert the command to run below. Here, we're just storing the date in a
## cron.log file
sh /home/groups/rbaltman/jlever/corona-ml/coronatime.sh

