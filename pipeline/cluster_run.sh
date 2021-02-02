#!/bin/bash
#
#SBATCH --job-name=coronaPipeline
#
#SBATCH --time=24:00:00
#SBATCH -p rbaltman
#SBATCH --mem=16G

set -ex

#snakemake --cores 1 -p data/alldocuments.ner.json
snakemake --cores 1 -p data/coronacentral.json

