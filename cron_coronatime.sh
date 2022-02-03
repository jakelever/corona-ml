#!/bin/bash
#SBATCH --job-name=cronCoronaCentral
#SBATCH --begin=now+12hours
#SBATCH --dependency=singleton
#SBATCH --time=11:00:00
#SBATCH --mail-type=FAIL
#SBATCH --mem=48G
#SBATCH -p rbaltman
set -ex

if [ -n $SLURM_JOB_ID ] ; then
	thisscript=$(scontrol show job $SLURM_JOBID | awk -F= '/Command=/{print $2}' | xargs realpath)
else
	thisscript=$(realpath $0)
fi

## Resubmit the job for the next execution
sbatch $thisscript

## Insert the command to run below. Here, we're just storing the date in a
## cron.log file

base=$(dirname $thisscript)
sh $base/coronatime.sh

