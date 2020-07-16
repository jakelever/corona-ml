import argparse
import json
from utils import dbconnect,load_documents_with_annotations
from utils import filter_languages

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Annotate documents with publication type (e.g. research article, review, news, etc)')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
	
	mydb = dbconnect()
	
	print("Loading documents with annotations...")
	documents = load_documents_with_annotations(args.inJSON,mydb)
	cleanup_documents(documents)
	
	assert all('entities' in d for d in documents), "Expected documents to already have entities extracted using NER"
	
	# Filter viruses by years
	for d in documents:
		if not d['publish_year']:
			continue
		viruses = sorted(set([ e['normalized'] for e in d['entities'] if e['type'] == 'Virus']))
		
		if d['publish_year'] < 2002 and 'SARS-CoV' in viruses:
			viruses.remove('SARS-CoV')
		if d['publish_year'] < 2012 and 'MERS-CoV' in viruses:
			viruses.remove('MERS-CoV')
		if d['publish_year'] < 2019 and 'SARS-CoV-2' in viruses:
			viruses.remove('SARS-CoV-2')
			
		if 'SARS-CoV-2' in viruses:
			viruses = ['SARS-CoV-2']
			
		d['entities'] = [ e for e in d['entities'] if e['type'] != 'Virus' or e['normalized'] in viruses ]
	
	print("Filtering for virus documents")
	viruses = {'SARS-CoV-2','SARS-CoV','MERS-CoV'}
	documents = [ d for d in documents if any(entity['type'] == 'Virus' for entity in d['entities']) or any( v in d['annotations'] for v in viruses) ]
	
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)