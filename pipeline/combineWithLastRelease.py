import argparse
import json
import gzip

def main():
	parser = argparse.ArgumentParser('Combine the output with the last release of CoronaCentral')
	parser.add_argument('--inJSON',required=True,type=str,help='Input JSON documents')
	parser.add_argument('--lastRelease',required=True,type=str,help='coronacentral.json.gz file from last release')
	parser.add_argument('--outJSONGZ',required=True,type=str,help='Output JSON GZ file')
	args = parser.parse_args()
		
	print("Loading last release documents...")
	added = 0
	with gzip.open(args.lastRelease,'rt') as f:
		documents = json.load(f)
		pubmed_ids = set( d['pubmed_id'] for d in documents )
		print(f"Loaded {len(documents)} documents from last release")

	print("Loading current run...")
	with gzip.open(args.inJSON,'rt') as f:
		current_run = json.load(f)
		print(f"Loaded {len(current_run)} documents from current run")
		for d in current_run:
			if d['pubmed_id'] not in pubmed_ids:
				pubmed_ids.add(d['pubmed_id'])
				documents.append(d)
				added += 1
	print(f"Added {added} documents from current run to last release")
			
	print("Saving data...")
	with gzip.open(args.outJSONGZ,'wt',encoding='utf8') as f:
		json.dump(documents,f)
	print(f"Saved {len(documents)} documents")

if __name__ == '__main__':
	main()

