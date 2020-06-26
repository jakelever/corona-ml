import SPARQLWrapper
import argparse
from collections import defaultdict,OrderedDict
import json
import re

def runQuery(query):
	endpoint = 'https://query.wikidata.org/sparql'
	sparql = SPARQLWrapper.SPARQLWrapper(endpoint)
	sparql.setQuery(query)
	sparql.setReturnFormat(SPARQLWrapper.JSON)
	results = sparql.query().convert()

	return results['results']['bindings']
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Tool to pull drug data from WikiData using SPARQL')
	parser.add_argument('--outJSON',type=str,required=True,help='File to output entities')
	args = parser.parse_args()

	totalCount = 0
	
	medication = 'Q12140'

	entities = defaultdict(dict)
	
	print("Gathering data from Wikidata...")
		
	query = """
	SELECT ?entity ?entityLabel ?entityDescription ?alias ?coords WHERE {
		SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
		?entity wdt:P31 wd:%s.
		OPTIONAL {?entity skos:altLabel ?alias FILTER (LANG (?alias) = "en") .}
	} 

	""" % medication

	rowCount = 0
	for row in runQuery(query):
		longID = row['entity']['value']
		
		if 'xml:lang' in row['entityLabel'] and row['entityLabel']['xml:lang'] == 'en':
		
			# Get the Wikidata ID, not the whole URL
			shortID = longID.split('/')[-1]
					
			entity = entities[shortID]
			entity['id'] = shortID
			entity['name'] = row['entityLabel']['value']
						
			if 'entityDescription' in row and 'xml:lang' in row['entityDescription'] and row['entityDescription']['xml:lang'] == 'en':
				entity['description'] = row['entityDescription']['value']
			
			if not 'aliases' in entity:
				entity['aliases'] = []

			if 'alias' in row and row['alias']['xml:lang'] == 'en':
				entity['aliases'].append(row['alias']['value'])

		rowCount += 1
		totalCount += 1

	for entityID,entity in entities.items():
		entity['aliases'].append(entity['name'])
		entity['aliases'] = [ t for t in entity['aliases'] if len(t) > 3 ]
		entity['aliases'] += [ t.replace('\N{REGISTERED SIGN}','').strip() for t in entity['aliases'] ]
		entity['aliases'] = [ a.strip().lower() for a in entity['aliases'] ]
		entity['aliases'] = [ a for a in entity['aliases'] if not '/' in a ]
		entity['aliases'] = sorted(set(entity['aliases']))
		
	entities = { entityID:entity for entityID,entity in entities.items() if len(entity['aliases']) > 0 }
	
	# Remove entities with '/' in their name
	entities = { entityID:entity for entityID,entity in entities.items() if not '/' in entity['name'] }	
	
	print ("  Got %d entities (from %d rows)" % (len(entities),totalCount))

	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		#entities_as_list = [ entities[entityID] for entityID in sorted(entities.keys()) ]
		json.dump(entities,f,indent=2,sort_keys=True)


