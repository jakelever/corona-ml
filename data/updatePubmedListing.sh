#!/bin/bash
set -ex

rm -f pubmed_listing.txt
for dir in "baseline" "updatefiles"
do
	ftpPath=ftp://ftp.ncbi.nlm.nih.gov/pubmed/$dir/

	curl --silent $ftpPath |\
	grep -oP "pubmed\w+.xml.gz" |\
	sort -u |\
	awk -v ftpPath=$ftpPath ' { print ftpPath$0 } ' >> pubmed_listing.txt
done

#curl --silent ftp://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/ | grep -oP "pubmed\w+.xml.gz" | sort -u >> pubmed_listing.txt

