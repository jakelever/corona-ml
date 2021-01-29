import argparse
import json

def main():
	parser = argparse.ArgumentParser('Create annotation data to load into the CoronaCentral database for use on the website')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with annotations')
	args = parser.parse_args()
	
	print("Loading documents...")
	with open(args.inJSON) as f:
		documents = json.load(f)
	
	autoannotations = []
	#locations = []
	for d in documents:
		if not any(entity['type'] == 'Virus' for entity in d['entities']):
			continue
			
		cord_uid = d['cord_uid']
		pubmed_id = d['pubmed_id']
		doi = d['doi']
		url = d['url']
		
		assert cord_uid or pubmed_id or doi or url
		
		for category in d['categories']:
			aa = { 'cord_uid': cord_uid, 'pubmed_id':pubmed_id, 'doi':doi, 'url':url, 'entity_type':'category', 'entity_name':category, 'external_id':'category_%s' % category, 'is_positive':True }
			autoannotations.append(aa)
			
		#uniqueEntities = sorted(set([ (entity['id'],entity['type'],entity['normalized']) for entity in d['entities'] ]))
		for entity in d['entities']:
			#aa = { 'cord_uid': cord_uid, 'pubmed_id':pubmed_id, 'entity_type':entityType, 'entity_name':entityNormalized, 'external_id':entityID, 'is_positive':True}
			aa = { 'cord_uid': cord_uid, 'pubmed_id':pubmed_id, 'doi':doi, 'url':url, 'entity_type':entity['type'], 'entity_name':entity['normalized'], 'external_id':entity['id'], 'start_pos':entity['start'], 'end_pos':entity['end'], 'section':entity['section'] }
			autoannotations.append(aa)
			
	#output = { 'annotations':autoannotations, 'locations':locations }
			
	with open(args.outJSON,'w') as outF:
		json.dump(autoannotations,outF,indent=2,sort_keys=True)

if __name__ == '__main__':
	main()

