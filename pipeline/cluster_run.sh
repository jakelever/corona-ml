#!/bin/bash
#
#SBATCH --job-name=coronaPipeline
#
#SBATCH --time=4:00:00
#SBATCH -p rbaltman
#SBATCH --mem=64G
#SBATCH --gpus 1

set -ex

snakemake --cores 1 data/autoannotations.json data/altmetric.json

