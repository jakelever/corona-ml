#!/bin/bash
set -ex

BASE=$PWD

# Download the last release of CoronaCentral from Zenodo
bash fetch_last_release.sh

# Download the preprepared term lists from Zenodo
mkdir pipeline/data
zenodo_get -o pipeline/data -d https://doi.org/10.5281/zenodo.8138562

# Download and preprocess new PubMed files (removing previously processed docs)
cd $BASE/data
bash run_update.sh

# Run the pipeline
cd $BASE/pipeline
gunzip -c pipeline/annotations.json.gz > pipeline/annotations.json
snakemake --cores 1

