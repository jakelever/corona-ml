import kindred
import argparse
import pickle
import json
from collections import defaultdict,Counter
import sys
import os
import time
import gzip

def chunks(lst, n):
	"""Yield successive n-sized chunks from lst."""
	for i in range(0, len(lst), n):
		yield lst[i:i + n]

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
		
def nice_time(seconds):
	days = int(seconds) // (24*60*60)
	seconds -= days * (24*60*60)
	hours = int(seconds) // (60*60)
	seconds -= hours * (60*60)
	minutes = int(seconds) // (60)
	seconds -= minutes * (60)
	
	bits = []
	if days:
		bits.append( "1 day" if days == 1  else "%d days" % days)
	if hours:
		bits.append( "1 hour" if hours == 1 else "%d hours" % hours)
	if minutes:
		bits.append( "1 minute" if minutes == 1 else "%d minutes" % minutes)
	bits.append( "1 second" if seconds == 1 else "%.1f seconds" % seconds)
	
	return ", ".join(bits)

def estimateTime(start_time,num_completed,num_total):
	now = time.time()
	perc = 100*num_completed/num_total
	
	time_so_far = (now-start_time)
	time_per_item = time_so_far / (num_completed+1)
	remaining_items = num_total - num_completed
	remaining_time = time_per_item * remaining_items
	total_time = time_so_far + remaining_time
	
	print("Completed %.1f%% (%d/%d)" % (perc,num_completed,num_total))
	print("time_per_item = %.4fs" % time_per_item)
	print("remaining_items = %d" % remaining_items)
	print("time_so_far = %.1fs (%s)" % (time_so_far,nice_time(time_so_far)))
	print("remaining_time = %.1fs (%s)" % (remaining_time,nice_time(remaining_time)))
	print("total_time = %.1fs (%s)" % (total_time,nice_time(total_time)))
	print('-'*30)
	print()
	sys.stdout.flush()

def main():
	parser = argparse.ArgumentParser('Run named entity recognition on parsed documents and integrate it into the JSON data')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--prevJSON',type=str,required=False,help='Optional previously processed output (to save time)')
	parser.add_argument('--entities',required=True,type=str,help='JSON file with listing of different JSON files with entities to load')
	parser.add_argument('--stopwords',required=True,type=str,help='File with stopwords to remove')
	parser.add_argument('--removals',required=True,type=str,help='File with entities to remove')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()

	ner_map = {}
	if args.prevJSON and os.path.isfile(args.prevJSON):
		with gzip.open(args.prevJSON,'rt') as f:
			prev_documents = json.load(f)

		for d in prev_documents:
			ner_key = (d['title'],d['abstract'])
			ner_map[ner_key] = d['entities']

	with gzip.open(args.inJSON,'rt') as f:
		documents = json.load(f)

	needs_doing = []
	already_done = []
	for d in documents:
		ner_key = (d['title'],d['abstract'])
		if ner_key in ner_map:
			d['entities'] = ner_map[ner_key]
			already_done.append(d)
		else:
			needs_doing.append(d)

	print("%d documents previously processed" % len(already_done))
	print("%d documents to be processed" % len(needs_doing))
	print()
	
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
	
	print("Annotating corpus...")
	sys.stdout.flush()

	chunk_size = 1000

	start_time = time.time()
	for chunk_no,document_chunk in enumerate(chunks(needs_doing,chunk_size)):
		estimateTime(start_time,chunk_no*chunk_size,len(needs_doing))

		corpus = kindred.Corpus()

		for d in document_chunk:	
			title_plus_abstract = d['title'] + "\n" + d['abstract']
			kindred_doc = kindred.Document(title_plus_abstract)
			corpus.addDocument(kindred_doc)

		parser = kindred.Parser(model='en_core_sci_sm')
		parser.parse(corpus)

		ner = kindred.EntityRecognizer(termLookup, mergeTerms=True)
		ner.annotate(corpus)

		assert len(document_chunk) == len(corpus.documents)

		for d,kindred_doc in zip(document_chunk,corpus.documents):
			
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
				
			# Filter locations to be capitalization matches
			entities = [ e for e in entities if doesLocationCapitalizationMatch(allEntities,e) ]
				
			#if kindred_doc.metadata['cord_uid'] == 'zpv5f8pr':
			#	print(json.dumps(entities,indent=2,sort_keys=True))
			d['entities'] = entities
		

	output_documents = already_done + needs_doing

	entity_counter = Counter( [ e['type'] for d in output_documents for e in d['entities'] ] )
	print("Found:", entity_counter)

	assert len(documents) == len(output_documents)
	assert all('entities' in d for d in output_documents), "Expected documents to all have entities extracted"
	
	print("Saving...")
	with gzip.open(args.outJSON,'wt') as f:
		json.dump(output_documents,f,indent=2,sort_keys=True)
		
if __name__ == '__main__':
	main()

