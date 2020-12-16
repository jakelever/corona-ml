#!/bin/bash
set -ex

bash updatePubmedListing.sh 

snakemake --cores 1

bash downloadCORD19_metadataOnly.sh 

python collectAllPapers.py --cord19Metadata cord19/metadata.csv --pubmed pubmed_corona/ --outFile ../pipeline/data/alldocuments.json

