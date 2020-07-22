import argparse
from collections import Counter
import json

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Clean up the associated URLs in documents and remove ones without usable URLs')
	parser.add_argument('--inJSON',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--outJSON',required=True,type=str,help='JSON file with fewer documents')
	args = parser.parse_args()

	print("Loading...")
	with open(args.inJSON) as f:
		documents = json.load(f)
		
	filtered = []

	for d in documents:
			
		if d['pubmed_id']:
			d['url'] = "https://pubmed.ncbi.nlm.nih.gov/%s" % d['pubmed_id']
		elif d['doi']:
			d['url'] = "https://doi.org/%s" % d['doi']
		elif d['pmcid']:
			d['url'] = "https://www.ncbi.nlm.nih.gov/pmc/articles/%s" % d['pmcid']
		elif d['url']:
			urls = [ u.strip() for u in d['url'].split(';') ]
			d['url'] = urls[0]
		else:
			d['url'] = None
			#print(json.dumps(d,indent=2,sort_keys=True))
			#assert False
	
	filtered = documents
	
	print("%d documents before final filtering" % len(filtered))
	
	filtered = [ d for d in filtered if not d['url'] is None ]
	
	print("%d documents after removing those without a usable URL" % len(filtered))
	
	filtered = [ d for d in filtered if not ('NotRelevant' in d['annotations'] or 'RemoveFromCorpus?' in d['annotations']) ]
	print("%d documents after removing that are manually flagged for removal" % len(filtered))
			
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(filtered,f,indent=2,sort_keys=True)
	