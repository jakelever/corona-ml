#!/bin/bash
#SBATCH --job-name=cronCoronaCentral
#SBATCH --begin=now+8hours
#SBATCH --dependency=singleton
#SBATCH --time=12:00:00
#SBATCH --mail-type=FAIL
#SBATCH --mem=48G
#SBATCH -p rbaltman
set -ex

## Resubmit the job for the next execution
sbatch $0

## Insert the command to run below. Here, we're just storing the date in a
## cron.log file

if [ -n $SLURM_JOB_ID ] ; then
	base=$(scontrol show job $SLURM_JOBID | awk -F= '/Command=/{print $2}' | xargs dirname)
else
	base=$(dirname "$0")
fi

sh $base/coronatime.sh

