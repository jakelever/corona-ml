#!/bin/bash
set -ex

listingURL="https://pages.semanticscholar.org/coronavirus-research"

outDir="kaggle"
rm -fr $outDir
mkdir $outDir
cd $outDir

curl -s $listingURL | grep -oP "https://ai2-semanticscholar-cord.[^\"]*" > filelisting.txt

cat filelisting.txt | xargs -I URL wget URL

find ./ -name '*.tar.gz' | xargs -I FILE sh -c "tar xvf FILE; rm FILE"
find ./ -name '*.gz' | xargs -I FILE sh -c "gunzip FILE"

