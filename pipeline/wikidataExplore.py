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
	parser = argparse.ArgumentParser(description='Tool to explore terms inherited from a Wikidata term')
	parser.add_argument('--parentID',type=str,required=True,help='WikiData ID to find all children of')
	#parser.add_argument('--inheritType',type=str,required=True,help='Whether through subclass or instanceof')
	args = parser.parse_args()
	
	query = """
		SELECT ?entity ?entityLabel WHERE {
			SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
			?entity wdt:P279* wd:%s.
		} 
	""" % args.parentID
	
	for row in runQuery(query):
		if 'xml:lang' in row['entityLabel'] and row['entityLabel']['xml:lang'] == 'en':
			entityID = row['entity']['value'].split('/')[-1]
			entityName = row['entityLabel']['value']
			print("%s\t%s" % (entityID,entityName))
			
			
			