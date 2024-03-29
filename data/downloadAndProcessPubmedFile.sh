#!/bin/bash

if [ $# -ne 2 ]; then
	echo "ERROR! Expected two arguments"
	echo
	echo "Usage: bash $0 pubmedFilename outputFilename"
	exit 1
fi

pubmedFilename=$1
outputFilename=$2

urlCount=`grep $pubmedFilename pubmed_listing.txt | wc -l`
if [[ $urlCount -ne 1 ]]; then
	echo "ERROR: Provided filename ($filename) doesn't give unique file URL from pubmed_listing.txt"
	echo "Found $urlCount matching line(s)"
	exit 1
fi

url=`grep $pubmedFilename pubmed_listing.txt`

python filterPubMedForCoronaPapersByKeyword.py --inURL $url --lastRelease ../last_release/process_record.json.gz --virusKeywords ../pipeline/predefined/terms_viruses.json --outFile $outputFilename

