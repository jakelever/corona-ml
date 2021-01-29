import argparse
import json
from collections import defaultdict

def main():
	parser = argparse.ArgumentParser('Annotate documents with publication type (e.g. research article, review, news, etc)')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--annotations',required=True,type=str,help='JSON file with annotations data from annotation platform')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
		
	print("Loading annotations")
	with open(args.annotations) as f:
		annotations = json.load(f)
		
	annotations_by_cord = defaultdict(list,annotations['annotations_by_cord'])
	annotations_by_pubmed_id = defaultdict(list,annotations['annotations_by_pubmed_id'])
	
	print("Loading documents...")
	with open(args.inJSON) as f:
		documents = json.load(f)
	
	print("Integrating annotations")
	for doc in documents:
		cord_uid = doc['cord_uid']
		pubmed_id = doc['pubmed_id']
		
		if 'annotations' in doc:
			doc['annotations'] = set(doc['annotations'])
		else:
			doc['annotations'] = set()
			
		doc['annotations'].update(annotations_by_cord[cord_uid])
		doc['annotations'].update(annotations_by_pubmed_id[pubmed_id])
			
		if 'ids_from_merged_documents' in doc:
			for tmp_cord_uid in doc['ids_from_merged_documents']['cord_uid']:
				doc['annotations'].update(annotations_by_cord[tmp_cord_uid])
			for tmp_pubmed_id in doc['ids_from_merged_documents']['pubmed_id']:
				doc['annotations'].update(annotations_by_pubmed_id[tmp_pubmed_id])
			
		doc['annotations'] = sorted(list(doc['annotations']))
	
	docCountWithAnnotations = len( [ doc for doc in documents if len(doc['annotations']) > 0 ] )
	
	print("Integrated annotations into %d documents" % docCountWithAnnotations)
	
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)

if __name__ == '__main__':
	main()

