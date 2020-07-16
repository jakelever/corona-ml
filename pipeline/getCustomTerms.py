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
	parser = argparse.ArgumentParser(description='Tool to pull custom data from WikiData using SPARQL')
	parser.add_argument('--termsToExpand',type=str,required=True,help='TSV with terms to look up in Wikidata')
	parser.add_argument('--predefined',type=str,required=True,help='JSON set of custom terms to simply add into result')
	parser.add_argument('--outJSON',type=str,required=True,help='File to output entities')
	args = parser.parse_args()

	entities = defaultdict(dict)
	print("Loading and expanding terms using Wikidata...")
	with open(args.termsToExpand) as f:
		for line in f:
			entityType,wikidataID,terms = line.strip('\n').split('\t')
			terms = terms.split('|')
			mainTerm = terms[0]
			
			query = """
			SELECT ?entityLabel WHERE {
				SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
				wd:%s rdfs:label ?entityLabel.
			} 

			""" % wikidataID

			entity = entities[wikidataID]
			entity['id'] = wikidataID
			entity['type'] = entityType
			entity['name'] = mainTerm
			entity['aliases'] = terms
					
			for row in runQuery(query):
				#print(row)
				if 'xml:lang' in row['entityLabel'] and row['entityLabel']['xml:lang'] == 'en':
					
					entityLabel = row['entityLabel']['value']
					entity['aliases'].append(entityLabel)
					
						
	
	print("Loading predefined...")
	with open(args.predefined) as f:
		predefined = json.load(f)
		entities.update(predefined)
		
	for entityID,entity in entities.items():
		entity['aliases'] = sorted(set(entity['aliases']))

	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		#entities_as_list = [ entities[entityID] for entityID in sorted(entities.keys()) ]
		json.dump(entities,f,indent=2,sort_keys=True)


