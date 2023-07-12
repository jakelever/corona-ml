#!/bin/bash
set -ex

bash updatePubmedListing.sh 

snakemake --cores 1 -T 3

python collectAllPapers.py --pubmed pubmed_corona/ --outFile ../pipeline/data/alldocuments.json.gz

