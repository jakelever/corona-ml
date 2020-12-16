#!/bin/bash
set -ex

outdir=$PWD/cord19
tmp_cord=$SCRATCH/tmp_cord

mkdir -p $outdir

rm -fr $tmp_cord
mkdir $tmp_cord
cd $tmp_cord

curl --silent https://ai2-semanticscholar-cord-19.s3-us-west-2.amazonaws.com/historical_releases.html |\
grep -oP "https://ai2-semanticscholar-cord-19.s3-us-west-2.amazonaws.com/historical_releases/cord-19_.*?.tar.gz" |\
sort |\
tail -n 1 > cord19_listing.txt

file_url_count=`cat cord19_listing.txt | wc -l`
if [[ $file_url_count -ne 1 ]]; then
	echo "ERROR: Couldn't find URL of latest CORD-19 file"
	exit 1
fi

file_date=`grep -oP "\d\d\d\d-\d\d-\d\d" cord19_listing.txt`
file_url=`cat cord19_listing.txt`

need_download=1
if [ -f $outdir/date.txt ]; then
	prev_date=`cat $outdir/date.txt`
	echo "Found previous download with date: $prev_date"
	if [[ "$file_date" == "$prev_date" ]]; then
		echo "Already got this version, so will not download"
		need_download=0
	fi
fi

if [ $need_download -eq 1 ]; then
	wget -nv $file_url

	tar -zxvf cord-19_$file_date.tar.gz $file_date/metadata.csv

	mv $file_date/metadata.csv $outdir/metadata.csv
	touch $outdir/metadata.csv
	echo $file_date > $outdir/date.txt
fi

cd -
rm -fr $tmp_cord

