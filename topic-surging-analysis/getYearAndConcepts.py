import argparse
import os
import bioc
from collections import defaultdict,Counter
import json
import sys

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Output PMIDs, years and biomedical concepts mentioned in abstracts')
	parser.add_argument('--aligned',required=True,type=str,help='Directory with PubTator aligned against documents')
	parser.add_argument('--outFile',required=True,type=str,help='Output file')
	args = parser.parse_args()

	filenames = [ f for f in os.listdir(args.aligned) if f.startswith('pubmed') and f.endswith('.bioc.xml') ]
		
	pmidsAlreadySeen = set()

	conceptsByYear = defaultdict(Counter)

	for filename in sorted(filenames,reverse=True):
		print("Processing %s" % filename)
		sys.stdout.flush()

		pmidsInThisFile = set()

		with open(os.path.join(args.aligned,filename),'rb') as f:
			parser = bioc.BioCXMLDocumentReader(f)
			for i,doc in enumerate(parser):
					
				if not('pmid' in doc.infons and doc.infons['pmid']):
					continue
				if not('year' in doc.infons and doc.infons['year']):
					continue

				year = int(doc.infons['year'])
				pmid = int(doc.infons['pmid'])
				#print(json.dumps(doc.infons,indent=2,sort_keys=True))
				if pmid in pmidsAlreadySeen:
					continue
				pmidsInThisFile.add(pmid)

				concepts = [ (a.infons['type'],a.infons['conceptid']) for p in doc.passages for a in p.annotations ]
				concepts = [ (conceptType,conceptID) for conceptType,conceptID in concepts if conceptType != 'Species' ]
				concepts = [ (conceptType,conceptID) for conceptType,conceptID in concepts if conceptID != '-' ]
				concepts = sorted(set(concepts))

				for conceptType,conceptID in concepts:
					conceptsByYear[year][(conceptType,conceptID)] += 1

		pmidsAlreadySeen.update(pmidsInThisFile)

	print("Saving...")
	sys.stdout.flush()

	with open(args.outFile,'w') as f:
		for year in conceptsByYear:
			for (conceptType,conceptID),count in conceptsByYear[year].items():
				f.write("%d\t%d\t%s\t%s\n" % (count,year,conceptType,conceptID))

	print("Done")

