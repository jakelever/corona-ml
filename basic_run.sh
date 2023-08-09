#!/bin/bash
set -ex

# Download the last release of CoronaCentral from Zenodo
bash fetch_last_release.sh

# Download the preprepared term lists from Zenodo
mkdir -p pipeline/data
zenodo_get -o pipeline/data -d https://doi.org/10.5281/zenodo.8138562

# Unzip the annotations file
gunzip -c pipeline/annotations.json.gz > pipeline/annotations.json

# Download and preprocess new PubMed files (removing previously processed docs)
cd data
bash run_update.sh

# Run the pipeline
cd ../pipeline
snakemake --cores 1

cd ../database
bash reload_db.sh

cd ..
aws_login=`cat aws_login.txt`
ssh -i aws_time.pem $aws_login ". ~/.bash_profile && cd corona-web && sh redeploy.sh"

bigzenodo --submission submission.json --accessTokenFile zenodo_token.txt --publish

