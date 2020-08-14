import argparse
from collections import Counter
import json
import os

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Clean up the associated URLs in documents and remove ones without usable URLs')
	parser.add_argument('--inJSON',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--outJSON',required=True,type=str,help='JSON file with fewer documents')
	args = parser.parse_args()

	print("Loading...")
	with open(args.inJSON) as f:
		documents = json.load(f)
		
	filtered = documents
	if os.path.isfile('checks.json'):
		with open('checks.json') as f:
			checks = json.load(f)
			
		filtered = [ d for d in filtered if not d['doi'] in checks ]
	
	print("%d documents before final filtering" % len(filtered))
	
	filtered = [ d for d in filtered if not d['url'] is None ]
	
	print("%d documents after removing those without a usable URL" % len(filtered))
	
	filtered = [ d for d in filtered if not ('NotRelevant' in d['annotations'] or 'RemoveFromCorpus?' in d['annotations']) ]
	print("%d documents after removing that are manually flagged for removal" % len(filtered))
	
	print("Cleaning up...")
	for d in documents:
		if 'web_articletypes' in d:
			del d['web_articletypes']
			
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(filtered,f,indent=2,sort_keys=True)
	