import argparse
import json
from collections import Counter,defaultdict
import re

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Apply some minor spotfixes to go in at the beginning of the pipeline')
	parser.add_argument('--inJSON',required=True,type=str,help='Input JSON documents')
	parser.add_argument('--spotfixes',required=True,type=str,help='List of mini fixes to corpus')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with added metadata')
	args = parser.parse_args()
	
	print("Loading documents...")
	with open(args.inJSON) as f:
		documents = json.load(f)
		
	print("Applying spot fixes...")
	with open(args.spotfixes) as f:
		spotfixes = json.load(f)
		
	for spotfix in spotfixes:
		field,fix_from,fix_to = spotfix['field'],spotfix['from'],spotfix['to']
		search = [ d for d in documents if d[field] == fix_from ]
		assert len(search) > 0, "Couldn't find documents for spotfix: %s" % str(spotfix)
		for d in search:
			d[field] = fix_to
		
	print("Saving data...")
	with open(args.outJSON,'w',encoding='utf8') as f:
		json.dump(documents,f)