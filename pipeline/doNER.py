import kindred
import argparse
import pickle
import json
from collections import defaultdict,Counter

def doesLocationCapitalizationMatch(allEntities,e):
	if e['type'] != 'location':
		return True
		
	aliases = allEntities[e['id']]['aliases']
	return e['text'] in aliases
		
if __name__ == '__main__':
	parser = argparse.ArgumentParser('Run named entity recognition on parsed documents and integrate it into the JSON data')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--drugs',required=True,type=str,help='JSON file with drug entities')
	parser.add_argument('--geonames',required=True,type=str,help='JSON file with geographic entities')
	parser.add_argument('--inParsed',required=True,type=str,help='Filename of Kindred corpus')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
	
	print("Loading wordlists...")
		
	nerFiles = {'drug':args.drugs,'location':args.geonames}
	
	allEntities = {}
	termLookup = defaultdict(set)
	for entityType,filename in nerFiles.items():
		with open(filename,encoding='utf8') as f:
			entityData = json.load(f)
				
			allEntities.update(entityData)
			
			for entityID,entity in entityData.items():
				for alias in entity['aliases']:
					termLookup[alias.lower()].add((entityType,entityID))

	virus_keywords = {}
	virus_keywords[('SARS-CoV-2','Q82069695')] = ['covid','covid-19','covid 19','sars-cov-2','sars cov 2','sars-cov 2','sars cov-2','sars-cov2','sars cov2','sarscov2','2019-ncov','2019 ncov','ncov19','ncov-19','ncov 19','ncov2019','ncov-2019','ncov 2019','(sars)-cov-2','(sars) cov 2','(sars)-cov 2','(sars) cov-2','(sars)-cov2','(sars) cov2','(sars)cov2','severe acute respiratory syndrome coronavirus 2','2019 novel coronavirus','novel 2019 coronavirus']
	virus_keywords[('SARS-CoV','Q85438966')] = ['sars','sars-cov','sars cov','sars-cov-1','sars cov 1','sars-cov 1','sars cov-1','sars-cov1','sars cov1','sarscov1','severe acute respiratory syndrome', '(sars)-cov','(sars) cov','(sars)-cov-1','(sars) cov 1','(sars)-cov 1','(sars) cov-1','(sars)-cov1','(sars) cov1','(sars)cov1', 'sars virus']
	virus_keywords[('MERS-CoV','Q4902157')] = ['mers','middle east respiratory syndrome','mers-cov','mers cov','mers-cov','mers cov','mers cov','mers-cov','merscov','(mers)-cov','(mers) cov','(mers)-cov','(mers) cov','(mers) cov','(mers)-cov','(mers)cov','mers virus']

	for (virus,entityID),keywords in virus_keywords.items():
		for keyword in keywords:
			termLookup[keyword.lower()].add(('virus',entityID))
			allEntities[entityID] = {'id':entityID,'name':virus}
			
	termLookup['k-mers'].add(('conflicting','Q6322851'))
	allEntities['Q6322851'] = {'id':'Q6322851','name':'k-mers'}

	manualChemicalAdditions = {}
	manualChemicalAdditions['Q200253'] = ['traditional chinese medicine','chinese herbal medicine','emodin']
	manualChemicalAdditions['Q28209496'] = ['remdesivir']
	manualChemicalAdditions['Q603502'] = ['convalescent plasma']
	manualChemicalAdditions['Q798309'] = ['bcg vaccine','bacillus calmette guerin vaccine']

	for chemicalID,chemicalNames in manualChemicalAdditions.items():
		for chemicalName in chemicalNames:
			termLookup[chemicalName.lower()].add(('chemical',chemicalID))
			
		mainTerm = chemicalNames[0]
		allEntities[chemicalID] = {'id':entityID,'name':mainTerm}
		 
	termLookup = defaultdict(set,{ k:v for k,v in termLookup.items() if not '/' in k })
	
	print("Loading and annotating corpus...")
	with open(args.inParsed,'rb') as f:
		corpus = pickle.load(f)
		
	corpus.removeEntities()
	ner = kindred.EntityRecognizer(termLookup)
	ner.annotate(corpus)
	
	print("Loading and integrating with JSON file...")
	with open(args.inJSON) as f:
		documents = json.load(f)
	
	key_items = ['url','title','cord_uid','pubmed_id','doi']
	entity_map = {}
	for d in corpus.documents:
		title = d.metadata['title']
		entities = []
		for e in d.entities:
			startPos = e.position[0][0]
			endPos = e.position[0][1]
			if endPos <= len(title):
				section = 'title'
			else:
				section = 'abstract'
				startPos -= len(title)+1
				endPos -= len(title)+1
				
			if ';' in e.externalID:
				continue
				
			normalized = allEntities[e.externalID]['name']
			
			entity = {''}
			entity = {'start':startPos,'end':endPos,'section':section,'id':e.externalID,'type':e.entityType,'text':e.text,'normalized':normalized,}
			entities.append(entity)
			
		key = tuple([ d.metadata[k] for k in key_items ])
		#print(entities)
		assert not key in entity_map
		entity_map[key] = entities
		
	for d in documents:
		key = tuple([ d[k] for k in key_items ])
		assert key in entity_map
		d['entities'] = entity_map[key]
		
		
	# Filter locations to be capitalization matches
	for d in documents:
		d['entities'] = [ e for e in d['entities'] if doesLocationCapitalizationMatch(allEntities,e) ]

	entity_counter = Counter( [ e['type'] for d in documents for e in d['entities'] ] )
	print("Found:", entity_counter)
		
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)
	
		