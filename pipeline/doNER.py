import kindred
import argparse
import pickle
import json
from collections import defaultdict,Counter
import sys

def doesLocationCapitalizationMatch(allEntities,e):
	if e['type'] != 'Location':
		return True
		
	aliases = allEntities[e['id']]['aliases']
	return e['text'] in aliases
	
def filterVirusesBasedOnPublishYear(d,kindred_doc):
	#virusIDs = {'SARS-CoV-2':'Q82069695','SARS-CoV':'Q85438966','MERS-CoV':'Q4902157'}
	
	SARS_CoV_2 = 'Q82069695'
	SARS_CoV = 'Q85438966'
	MERS_CoV = 'Q4902157'

	viruses = sorted(set([ e.externalID for e in kindred_doc.entities if e.entityType == 'Virus']))
	if d['publish_year']:
				
		if d['publish_year'] < 2002 and SARS_CoV in viruses:
			viruses.remove(SARS_CoV)
		if d['publish_year'] < 2012 and MERS_CoV in viruses:
			viruses.remove(MERS_CoV)
		if d['publish_year'] < 2019 and SARS_CoV_2 in viruses:
			viruses.remove(SARS_CoV_2)
			
	if SARS_CoV_2 in viruses:
		viruses = [SARS_CoV_2]
		
	kindred_doc.entities = [ e for e in kindred_doc.entities if e.entityType != 'Virus' or e.externalID in viruses ]
		
def undoMergingOfEntitiesInSamePosition(kindred_doc):
	entitiesWithoutMergedExternalIDs = []
	for e in kindred_doc.entities:
		for externalID in e.externalID.split(';'):
			e2 = e.clone()
			e2.externalID = externalID
			entitiesWithoutMergedExternalIDs.append(e2)
			
	kindred_doc.entities = entitiesWithoutMergedExternalIDs
		
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
	for nerFile in nerFiles:
		entityType = nerFile['type']
		filename = nerFile['filename']
		print("  %s\t%s" % (entityType,filename))
		with open(filename,encoding='utf8') as f:
			entityData = json.load(f)
			
			entityData = { entityID:entity for entityID,entity in entityData.items() if not entityID in idsToRemove }
				
			allEntities.update(entityData)
			
			for entityID,entity in entityData.items():
				if entityType != 'custom': 
					entity['type'] = entityType
				else:
					assert 'type' in entity # Custom entities must define their type internally
			
				aliases = entity['aliases']
				if 'ambiguous_aliases' in entity:
					aliases += entity['ambiguous_aliases']
					hasAmbiguities.append(entityID)
					
				aliases = [ a.lower() for a in aliases ]
				if len(specificSynonymsToRemove[entityID]) > 0:
					aliases = [ a for a in aliases if not a in specificSynonymsToRemove[entityID] ]
					
				for alias in aliases:
					termLookup[alias].add((entity['type'],entityID))
		 
	termLookup = defaultdict(set,{ k:v for k,v in termLookup.items() if not k in stopwords })
	
	print ("Checking that entities have unique primary names within each type...")
	uniqueNamesCheck = defaultdict(lambda : defaultdict(list))
	for entityID,entity in entityData.items():
		uniqueNamesCheck[entity['type']][entity['name'].lower()].append(entityID)
		
	uniqueCheckPassed = True
	for entityType in sorted(uniqueNamesCheck.keys()):
		notunique = { name:ids for name,ids in uniqueNamesCheck[entityType].items() if len(ids) > 1 }
		if len(notunique) > 0:
			uniqueCheckPassed = False
		for name,ids in notunique.items():
			print("  Not Unique: %s : %s : %s" % (entityType,name,str(ids)))
	
	assert uniqueCheckPassed, "Check FAILED!"
	
	
	
	print("Check PASSED!")
	print()
	
	#with open(nerFiles['Location'],encoding='utf8') as f:
	#	geoData = json.load(f)
	
	print("N.B. NO AMBIGUITY ALLOWED (in current implementation)")
	#termLookup = defaultdict(set,{ k:v for k,v in termLookup.items() if len(v) == 1 })
	
	print("Loading and integrating with JSON file...")
	with open(args.inJSON) as f:
		documents = json.load(f)
	
	
	#for alias,entities in termLookup.items():
	#	if len(entities) > 1:
	#		print("%s\t%d" % (alias,len(entities)))
	
	testMode = "fuh0qws1"
	
	
	if not testMode:
		print("Loading corpus...")
		sys.stdout.flush()
		with open(args.inParsed,'rb') as f:
			corpus = pickle.load(f)
	else:
		print("RUNNING IN TEST MODE for doc: %s" % testMode)
		
		documents = [ d for d in documents if d['cord_uid'] == testMode ]
		assert len(documents) == 1
		text = documents[0]['title'] + "\n" + documents[0]['abstract']
		
		print("Title: %s" % documents[0]['title'])
		print("Abstract: %s" % documents[0]['abstract'])
		
		corpus = kindred.Corpus(text = text)
		corpus.documents[0].metadata = {"title":documents[0]['title']}
		parser = kindred.Parser(model='en_core_sci_sm')
		parser.parse(corpus)
	
	print("Annotating corpus...")
	sys.stdout.flush()
	corpus.removeEntities()
	ner = kindred.EntityRecognizer(termLookup)
	ner.annotate(corpus)
	
	if testMode:
		doc = corpus.documents[0]
		for e in doc.entities:
			print("  %s" % str(e))
		#print(doc.entities) 	
	
	#assert False
	
	corpusMap = {}
	for kindred_doc in corpus.documents:
		corpusMap[kindred_doc.text] = kindred_doc

	for d in documents:				
		key = d['title'] + "\n" + d['abstract']
		kindred_doc = corpusMap[key]
		
		# Strip out some terms
		kindred_doc.entities = [ e for e in kindred_doc.entities if not e.entityType == 'conflicting' ]
		
		# This is "undoing" the merge of externalIDs for merged terms in Kindred
		undoMergingOfEntitiesInSamePosition(kindred_doc)
		
		# Clean up viruses so that they make sense given the publication year (and also if SARS-CoV-2 appears, it's a SARS-CoV-2 paper, and not another one - for now)
		filterVirusesBasedOnPublishYear(d,kindred_doc)
		
		virusesInDoc = sorted(set( allEntities[e.externalID]['name'] for e in kindred_doc.entities if e.entityType == 'Virus'))
		
		entitiesByPosition = defaultdict(list)
		for e in kindred_doc.entities:
			entitiesByPosition[e.position[0]].append(e)
			
		#unambigLocationCoords = []
		#for position,entitiesAtPosition in entitiesByPosition.items():
		#	if len(entitiesAtPosition) == 1 and entitiesAtPosition[0].entityType == 'Location':
		#		thisGeoData = geoData[entitiesAtPosition[0].externalID]
		#		coord = [thisGeoData['longitude'],thisGeoData['latitude']]
		#		unambigLocationCoords.append(coord)
	
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
			
			allEntitiesDependOnVirus = all( 'associated_virus' in allEntities[e.externalID] for e in entitiesAtPosition)
			if allEntitiesDependOnVirus:
				if len(virusesInDoc) != 1: # Ambiguous which virus in document, skip this one
					continue
					
				entitiesFilteredToVirus = []
				for e in entitiesAtPosition:
					virusForEntity = allEntities[e.externalID]['associated_virus']
					if virusForEntity == virusesInDoc[0]:
						entitiesFilteredToVirus.append(e)
						
				entitiesAtPosition = entitiesFilteredToVirus
					
			# Ambiguity remains so we skip it
			if len(entitiesAtPosition) != 1:
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

	assert all('entities' in d for d in documents), "Expected documents to all have entities extracted"
	
	print("Filtering for virus documents")
	viruses = {'SARS-CoV-2','SARS-CoV','MERS-CoV'}
	documents = [ d for d in documents if any(entity['type'] == 'Virus' for entity in d['entities']) or any( v in d['annotations'] for v in viruses) ]
		
	print("Saving JSON file...")
	sys.stdout.flush()
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)
	
		
