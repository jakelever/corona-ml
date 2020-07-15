import kindred
import argparse
import pickle
import json
from collections import defaultdict,Counter
from scipy.spatial import distance_matrix

def doesLocationCapitalizationMatch(allEntities,e):
	if e['type'] != 'location':
		return True
		
	aliases = allEntities[e['id']]['aliases']
	return e['text'] in aliases
		
if __name__ == '__main__':
	parser = argparse.ArgumentParser('Run named entity recognition on parsed documents and integrate it into the JSON data')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--viruses',required=True,type=str,help='JSON file with virus entities')
	parser.add_argument('--drugs',required=True,type=str,help='JSON file with drug entities')
	parser.add_argument('--geonames',required=True,type=str,help='JSON file with geographic entities')
	parser.add_argument('--custom',required=True,type=str,help='JSON file with custom additional entities')
	parser.add_argument('--inParsed',required=True,type=str,help='Filename of Kindred corpus')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
	
	print("Loading wordlists...")
		
	nerFiles = {'virus':args.viruses,'drug':args.drugs,'location':args.geonames,'custom':args.custom}
	
	allEntities = {}
	termLookup = defaultdict(set)
	for entityType,filename in nerFiles.items():
		with open(filename,encoding='utf8') as f:
			entityData = json.load(f)
				
			allEntities.update(entityData)
			
			for entityID,entity in entityData.items():
				for alias in entity['aliases']:
					tmpEntityType = entity['type'] if entityType == 'custom' else entityType
					termLookup[alias.lower()].add((tmpEntityType,entityID))
		 
	termLookup = defaultdict(set,{ k:v for k,v in termLookup.items() if not '/' in k })
	
	with open(args.geonames,encoding='utf8') as f:
		geoData = json.load(f)
	
	print("NO AMBIGUITY ALLOWED")
	termLookup = defaultdict(set,{ k:v for k,v in termLookup.items() if len(v) == 1 })
	
	#for alias,entities in termLookup.items():
	#	if len(entities) > 1:
	#		print("%s\t%d" % (alias,len(entities)))
	
	print("Loading and annotating corpus...")
	with open(args.inParsed,'rb') as f:
		corpus = pickle.load(f)
		
	#corpus = kindred.Corpus(text = "Reports are coming from Wuhan in China")
	#corpus.documents[0].metadata = {"title":"-"*100}
	#parser = kindred.Parser(model='en_core_sci_sm')
	#parser.parse(corpus)
	
	corpus.removeEntities()
	ner = kindred.EntityRecognizer(termLookup)
	ner.annotate(corpus)
	
	#doc = corpus.documents[0]
	#print(doc.entities) 	
	
	#assert False
	
	print("Loading and integrating with JSON file...")
	with open(args.inJSON) as f:
		documents = json.load(f)
	
	key_items = ['url','title','cord_uid','pubmed_id','doi']
	entity_map = {}
	for d in corpus.documents:
		title = d.metadata['title']
		
		unambigLocationCoords = []
		
		entitiesByPosition = defaultdict(list)
		for e in d.entities:
			entitiesByPosition[e.position[0]].append(e)
			
		for position,entitiesAtPosition in entitiesByPosition.items():
			if len(entitiesAtPosition) == 1 and entitiesAtPosition[0].entityType == 'location':
				thisGeoData = geoData[entitiesAtPosition[0].externalID]
				coord = [thisGeoData['longitude'],thisGeoData['latitude']]
				unambigLocationCoords.append(coord)
			
		entities = []
		for position,entitiesAtPosition in entitiesByPosition.items():
			#allAreLocations = all( e.entityType=='location' for e in entitiesAtPosition )
			
			# Only do disambiguation for locations
			#if len(entitiesAtPosition) > 1 and not allAreLocations and len(unambigLocationCoords) > 0:
			#	continue
			if len(entitiesAtPosition) > 1:
				continue
				
			#if allAreLocations:
			#	candidateCoords = []
			#	for e in entitiesAtPosition:
			#		thisGeoData = geoData[e.externalID]
			#		coord = [thisGeoData['longitude'],thisGeoData['latitude']]
			#		candidateCoords.append(coord)
			#	closestCandidateCoord = distance_matrix(unambigLocationCoords, candidateCoords).min(axis=0).argmin()
			#	entitiesAtPosition = [entitiesAtPosition[closestCandidateCoord]]
				
			e = entitiesAtPosition[0]
			
			startPos = position[0]
			endPos = position[1]
			if endPos <= len(title):
				section = 'title'
			else:
				section = 'abstract'
				startPos -= len(title)+1
				endPos -= len(title)+1
				
			normalized = allEntities[e.externalID]['name']
			
			entity = {''}
			entity = {'start':startPos,'end':endPos,'section':section,'id':e.externalID,'type':e.entityType,'text':e.text,'normalized':normalized}
			entities.append(entity)
			
		#print(entities)
			
		#if d.metadata['cord_uid'] == 'zpv5f8pr':
		#	print(json.dumps(entities,indent=2,sort_keys=True))
			
		key = tuple([ d.metadata[k] for k in key_items ])
		assert not key in entity_map, "Found duplicate document with key: %s" % str(key)
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
	
		