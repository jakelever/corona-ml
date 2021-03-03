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
cp test_documents.json testing_dir/data/alldocuments.json

# Move into the directory
cd testing_dir

# Unzip the annotated documents
gunzip -f annotations.json.gz

# Run the pipeline
snakemake --cores 1

