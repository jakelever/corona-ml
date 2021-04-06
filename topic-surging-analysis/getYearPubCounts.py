import argparse
import os
import bioc
from collections import defaultdict,Counter
import json
import sys

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Output publication counts per year')
	parser.add_argument('--aligned',required=True,type=str,help='Directory with PubTator aligned against documents')
	parser.add_argument('--outFile',required=True,type=str,help='Output file')
	args = parser.parse_args()

	filenames = [ f for f in os.listdir(args.aligned) if f.startswith('pubmed') and f.endswith('.bioc.xml') ]
		
	pmidToYear = {}

	for filename in sorted(filenames,reverse=True):
		print("Processing %s" % filename)
		sys.stdout.flush()

		with open(os.path.join(args.aligned,filename),'rb') as f:
			parser = bioc.BioCXMLDocumentReader(f)
			for i,doc in enumerate(parser):
					
				if not('pmid' in doc.infons and doc.infons['pmid']):
					continue
				if not('year' in doc.infons and doc.infons['year']):
					continue

				year = int(doc.infons['year'])
				pmid = int(doc.infons['pmid'])

				pmidToYear[pmid] = year

	yearCounts = Counter(pmidToYear.values())

	print("Saving...")
	sys.stdout.flush()

	with open(args.outFile,'w') as f:
		for year in sorted(yearCounts.keys(),reverse=True):
			f.write("%d\t%d\n" % (year,yearCounts[year]))

	print("Done")

