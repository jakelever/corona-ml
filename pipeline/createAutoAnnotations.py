import argparse
import json
import re
from collections import Counter

from utils import DocumentVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multiclass import OneVsRestClassifier

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Annotate the topics of the documents')
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
		
		for topic in d['topics']:
			aa = { 'cord_uid': cord_uid, 'pubmed_id':pubmed_id, 'entity_type':'topic', 'entity_name':topic, 'wikidata_id':None, 'is_positive':True }
			autoannotations.append(aa)
			
		#uniqueEntities = sorted(set([ (entity['id'],entity['type'],entity['normalized']) for entity in d['entities'] ]))
		for entity in d['entities']:
			#aa = { 'cord_uid': cord_uid, 'pubmed_id':pubmed_id, 'entity_type':entityType, 'entity_name':entityNormalized, 'external_id':entityID, 'is_positive':True}
			aa = { 'cord_uid': cord_uid, 'pubmed_id':pubmed_id, 'entity_type':entity['type'], 'entity_name':entity['normalized'], 'external_id':entity['id'], 'start_pos':entity['start'], 'end_pos':entity['end'], 'section':entity['section'] }
			autoannotations.append(aa)
			
		aa = { 'cord_uid': cord_uid, 'pubmed_id':pubmed_id, 'entity_type':'pubtype', 'entity_name':d['ml_pubtype'] }
		autoannotations.append(aa)
		
	#output = { 'annotations':autoannotations, 'locations':locations }
			
	with open(args.outJSON,'w') as outF:
		json.dump(autoannotations,outF,indent=2,sort_keys=True)  