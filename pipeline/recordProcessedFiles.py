import argparse
import json
import os
import gzip

def main():
	parser = argparse.ArgumentParser('Note which files and Pubmed IDs have been processed')
	parser.add_argument('--pubmedDir',required=True,type=str,help='Directory with PubMed files')
	parser.add_argument('--previousReleaseProcessedFiles',required=True,type=str,help='process_record.json.gz from previous release')
	parser.add_argument('--initialDocuments',required=True,type=str,help='Initial documents file')
	parser.add_argument('--finalRelease',required=True,type=str,help='Final file (gzipped)')
	parser.add_argument('--outJSONGZ',required=True,type=str,help='Output JSON GZ')
	args = parser.parse_args()
	
	with gzip.open(args.previousReleaseProcessedFiles) as f:
		pubmed_files = json.load(f)['pubmed_files']
	
	pubmed_files += sorted( [ f for f in os.listdir(args.pubmedDir) if f.startswith('pubmed') ] )
	pubmed_files = sorted(set(pubmed_files))
	
	print("Loading documents...")
	with gzip.open(args.initialDocuments,'rt') as f:
		documents = json.load(f)
		pubmed_ids = [ d['pubmed_id'] for d in documents if d['pubmed_id'] ]
	
	with gzip.open(args.finalRelease,'rt') as f:
		documents = json.load(f)
		pubmed_ids += [ d['pubmed_id'] for d in documents if d['pubmed_id'] ]
		
	pubmed_ids = sorted(set(pubmed_ids))
		
	print("Saving data...")
	with gzip.open(args.outJSONGZ,'wt') as f:
		output = {'pubmed_ids':pubmed_ids, 'pubmed_files':pubmed_files}
		json.dump(output,f)

if __name__ == '__main__':
	main()

