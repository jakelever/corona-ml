import kindred
import argparse
import pickle
import json
from collections import defaultdict,Counter
from scipy.spatial import distance_matrix

def doesLocationCapitalizationMatch(allEntities,e):
	if e['type'] != 'Location':
		return True
		
	aliases = allEntities[e['id']]['aliases']
	return e['text'] in aliases
		
if __name__ == '__main__':
	parser = argparse.ArgumentParser('Run named entity recognition on parsed documents and integrate it into the JSON data')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--entities',required=True,type=str,help='JSON file with listing of different JSON files with entities to load')
	parser.add_argument('--inParsed',required=True,type=str,help='Filename of Kindred corpus')
	parser.add_argument('--stopwords',required=True,type=str,help='File with stopwords to remove')
	parser.add_argument('--removals',required=True,type=str,help='File with entities to remove')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
	
	print("Loading wordlists...")
	
	with open(args.entities) as f:
		nerFiles = json.load(f)
		
	with open(args.stopwords) as f:
		stopwords = set( line.strip().lower() for line in f )
		
	idsToRemove, specificSynonymsToRemove = set(), defaultdict(set)
	with open(args.removals) as f:
		for line in f:
			#removals = set(line.strip('\n').split('\t')[0] for line in f)
			split = line.strip('\n').split('\t')
			assert len(split)==3, "Expected 3 columns on line: %s" % json.dumps([line])
			wikidataID, name, synonyms = split
			if synonyms:
				specificSynonymsToRemove[wikidataID].update(synonyms.lower().split('|'))
			else:
				idsToRemove.add(wikidataID)
	
	allEntities = {}
	termLookup = defaultdict(set)
	hasAmbiguities = []
	for entityType,filename in nerFiles.items():
		print("  %s\t%s" % (entityType,filename))
		with open(filename,encoding='utf8') as f:
			entityData = json.load(f)
			
			entityData = { entityID:entity for entityID,entity in entityData.items() if not entityID in idsToRemove }
				
			allEntities.update(entityData)
			
			for entityID,entity in entityData.items():
				aliases = entity['aliases']
				if 'ambiguous_aliases' in entity:
					aliases += entity['ambiguous_aliases']
					hasAmbiguities.append(entityID)
					
				aliases = [ a.lower() for a in aliases ]
				if len(specificSynonymsToRemove[entityID]) > 0:
					aliases = [ a for a in aliases if not a in specificSynonymsToRemove[entityID] ]
					
				for alias in aliases:
					tmpEntityType = entity['type'] if entityType == 'custom' else entityType
					termLookup[alias].add((tmpEntityType,entityID))
		 
	termLookup = defaultdict(set,{ k:v for k,v in termLookup.items() if not k in stopwords })
	
	with open(nerFiles['Location'],encoding='utf8') as f:
		geoData = json.load(f)
	
	print("NO AMBIGUITY ALLOWED")
	#termLookup = defaultdict(set,{ k:v for k,v in termLookup.items() if len(v) == 1 })
	
	#for alias,entities in termLookup.items():
	#	if len(entities) > 1:
	#		print("%s\t%d" % (alias,len(entities)))
	
	print("Loading corpus...")
	with open(args.inParsed,'rb') as f:
		corpus = pickle.load(f)
		
	#corpus = kindred.Corpus(text = "Reports are coming from Wuhan in China")
	#corpus.documents[0].metadata = {"title":"-"*100}
	#parser = kindred.Parser(model='en_core_sci_sm')
	#parser.parse(corpus)
	
	print("Annotating corpus...")
	corpus.removeEntities()
	ner = kindred.EntityRecognizer(termLookup, mergeTerms=True)
	ner.annotate(corpus)
	
	#doc = corpus.documents[0]
	#print(doc.entities) 	
	
	#assert False
	
	print("Loading and integrating with JSON file...")
	with open(args.inJSON) as f:
		documents = json.load(f)
	
	corpusMap = {}
	for kindred_doc in corpus.documents:
		corpusMap[kindred_doc.text] = kindred_doc

	for d in documents:
		key = d['title'] + "\n" + d['abstract']
		kindred_doc = corpusMap[key]
		
		# Strip out some terms
		kindred_doc.entities = [ e for e in kindred_doc.entities if not e.entityType == 'conflicting' ]
		
		# This is "undoing" the merge of externalIDs for merged terms in Kindred
		entitiesWithoutMergedExternalIDs = []
		for e in kindred_doc.entities:
			for externalID in e.externalID.split(';'):
				e2 = e.clone()
				e2.externalID = externalID
				entitiesWithoutMergedExternalIDs.append(e2)
		kindred_doc.entities = entitiesWithoutMergedExternalIDs
		
		
		virusesInDoc = sorted(set( allEntities[e.externalID]['name'] for e in kindred_doc.entities if e.entityType == 'Virus'))
		
		entitiesByPosition = defaultdict(list)
		for e in kindred_doc.entities:
			entitiesByPosition[e.position[0]].append(e)
			
		unambigLocationCoords = []
		for position,entitiesAtPosition in entitiesByPosition.items():
			if len(entitiesAtPosition) == 1 and entitiesAtPosition[0].entityType == 'Location':
				thisGeoData = geoData[entitiesAtPosition[0].externalID]
				coord = [thisGeoData['longitude'],thisGeoData['latitude']]
				unambigLocationCoords.append(coord)
	
		title = d['title']
		entities = []
		for position,entitiesAtPosition in entitiesByPosition.items():
			#allAreLocations = all( e.entityType=='Location' for e in entitiesAtPosition )
			
			# Only do disambiguation for locations
			#if len(entitiesAtPosition) > 1 and not allAreLocations and len(unambigLocationCoords) > 0:
			#	continue
				
			#if allAreLocations:
			#	candidateCoords = []
			#	for e in entitiesAtPosition:
			#		thisGeoData = geoData[e.externalID]
			#		coord = [thisGeoData['longitude'],thisGeoData['latitude']]
			#		candidateCoords.append(coord)
			#	closestCandidateCoord = distance_matrix(unambigLocationCoords, candidateCoords).min(axis=0).argmin()
			#	entitiesAtPosition = [entitiesAtPosition[closestCandidateCoord]]
			
			if e.externalID in hasAmbiguities:
				virusForEntity = allEntities[e.externalID]['associated_virus']
				if len(virusesInDoc) != 1: # Ambiguous which virus in document, skip this one
					continue
				elif virusForEntity != virusesInDoc[0]: # Skip because this entity is for the wrong virus!
					continue
					
				entitiesAtPosition = [e]
					
			# Ambiguity remains so we skip it
			if len(entitiesAtPosition) > 1:
				continue
				
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
			
		#if kindred_doc.metadata['cord_uid'] == 'zpv5f8pr':
		#	print(json.dumps(entities,indent=2,sort_keys=True))
		d['entities'] = entities
		
		
	# Filter locations to be capitalization matches
	for d in documents:
		d['entities'] = [ e for e in d['entities'] if doesLocationCapitalizationMatch(allEntities,e) ]

	entity_counter = Counter( [ e['type'] for d in documents for e in d['entities'] ] )
	print("Found:", entity_counter)
		
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)
	
		