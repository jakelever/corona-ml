#!/bin/bash
set -ex

# Set up a temporary testing directory (to not interfere with a pipeline run)

mkdir testing_dir
mkdir testing_dir/data

# Copy the relevant Python scripts and annotation data across
cp pipeline/*.py testing_dir
cp pipeline/Snakefile testing_dir
cp pipeline/annotations.json.gz testing_dir
cp pipeline/*.json testing_dir
cp -r pipeline/predefined testing_dir

# Copy the small test dataset into the data directory
gzip -c test_documents.json > testing_dir/data/alldocuments.json.gz

# Set up a dummy empty old release of CoronaCentral
rm -fr last_release
mkdir last_release
echo '[]' | gzip > last_release/coronacentral.json.gz
echo '{"pubmed_ids":[], "pubmed_files":[]}' | gzip > last_release/process_record.json.gz

# Move into the directory
cd testing_dir

# Unzip the annotated documents
gunzip -f annotations.json.gz

# Run the pipeline
snakemake --cores 1

