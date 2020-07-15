import argparse
from collections import Counter
import json

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Remove duplicate documents')
	parser.add_argument('--inJSON',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--outJSON',required=True,type=str,help='JSON file with fewer documents')
	args = parser.parse_args()

	print("Loading...")
	with open(args.inJSON) as f:
		documents = json.load(f)
		
	filtered = []

	seenPubmed,seenDOI,seenCORD = set(),set(),set()
	for d in documents:
		if d['pubmed_id'] and d['pubmed_id'] in seenPubmed:
			continue
		if d['doi'] and d['doi'] in seenDOI:
			continue
		if d['cord_uid'] and d['cord_uid'] in seenCORD:
			continue
			
		filtered.append(d)
		
		
		if d['pubmed_id']:
			seenPubmed.add(d['pubmed_id'])
		if d['doi']:
			seenDOI.add(d['doi'])
		if d['cord_uid']:
			seenCORD.add(d['cord_uid'])
			
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(filtered,f,indent=2,sort_keys=True)

	print("Removed %d duplicate documents" % (len(documents)-len(filtered)))
	