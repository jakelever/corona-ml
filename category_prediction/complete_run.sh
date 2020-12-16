#!/bin/bash
#
#SBATCH --job-name=corona_optimize
#
#SBATCH --time=96:00:00
#SBATCH -p rbaltman
#SBATCH --mem=4G

set -ex

snakemake -j 100 --cluster ' mysbatch -p rbaltman --mem 4G --gpus {params.gpucount} --time 4:00:00' --latency-wait 60 --nolock -p
#snakemake -j 100 --cluster ' mysbatch -p gpu --mem 16G --gpus 1' --latency-wait 60 --nolock

