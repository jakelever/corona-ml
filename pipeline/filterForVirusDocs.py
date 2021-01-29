import argparse
import json
from collections import defaultdict

def main():
	parser = argparse.ArgumentParser('Remove documents that do not contain virus names or annotations')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
		
	print("Loading documents...")
	with open(args.inJSON) as f:
		documents = json.load(f)

	print("Loaded %d documents" % len(documents))

	print("Filtering for virus documents")
	viruses = {'SARS-CoV-2','SARS-CoV','MERS-CoV'}
	for d in documents:
		d['viruses'] = [ e['normalized'] for e in d['entities'] if e['type'] == 'Virus' ]
		d['viruses'] += [ a for a in d['annotations'] if a in viruses ]
		d['viruses'] = sorted(set(d['viruses']))

	documents = [ d for d in documents if d['viruses'] ]
		
	print("Filtered to %d documents" % len(documents))
	
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)

if __name__ == '__main__':
	main()

