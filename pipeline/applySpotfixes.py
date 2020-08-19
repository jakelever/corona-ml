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
		identifier_field,identifier_value = None,None
		
		if 'doi' in spotfix:
			identifier_field = 'doi'
		elif 'pubmed_id' in spotfix:
			identifier_field = 'pubmed_id'
		elif 'cord_uid' in spotfix:
			identifier_field = 'cord_uid'
		
		assert identifier_field is not None, "Need doi, pubmed_id or cord_uid to identify spotfix"
		identifier_value = spotfix[identifier_field]
		
		field,fix_to = spotfix['field'],spotfix['to']
		search = [ d for d in documents if d[identifier_field] == identifier_value ]
		assert len(search) > 0, "Couldn't find documents for spotfix: %s" % str(spotfix)
		for d in search:
			d[field] = fix_to
		
	print("Saving data...")
	with open(args.outJSON,'w',encoding='utf8') as f:
		json.dump(documents,f)