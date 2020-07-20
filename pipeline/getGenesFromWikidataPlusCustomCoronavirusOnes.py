import SPARQLWrapper
import argparse
from collections import defaultdict,OrderedDict
import json
import re

def runQuery(query):
	endpoint = 'https://query.wikidata.org/sparql'
	sparql = SPARQLWrapper.SPARQLWrapper(endpoint, agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36')
	sparql.setQuery(query)
	sparql.setReturnFormat(SPARQLWrapper.JSON)
	results = sparql.query().convert()

	return results['results']['bindings']
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Tool to pull drug data from WikiData using SPARQL')
	parser.add_argument('--outJSON',type=str,required=True,help='File to output entities')
	args = parser.parse_args()

	totalCount = 0
	
	gene = 'Q7187'
	homo_sapiens = 'Q15978631'

	entities = defaultdict(dict)
	
	print("Gathering data from Wikidata...")
		
	query = """
	SELECT ?entity ?entityLabel ?entityDescription ?alias ?coords WHERE {
		SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
		?entity wdt:P31 wd:%s.
		?entity wdt:P703 wd:%s.
		OPTIONAL {?entity skos:altLabel ?alias FILTER (LANG (?alias) = "en") .}
	} 

	""" % (gene,homo_sapiens)

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
	
	print('Adding custom coronavirus proteins...')
	structural_proteins = ['envelope','spike','membrane']
	for virus in ['SARS-CoV-2','SARS-CoV','MERS-CoV']:
		for protein in structural_proteins:
			singleletter = protein[0].upper()
			
			virus_names = [virus, virus.replace('-',' '), virus.replace('-',' ').replace('CoV','coronavirus') ]
			if virus == 'SARS-CoV-2':
				virus_names.append('2019-nCoV')
			
			#entities['%s_spike'] = 
			aliases = []
			for tmp_virus in virus_names:
				aliases += [ '%s %s protein' % (tmp_virus,protein), '%s %s protein' % (tmp_virus,singleletter), '%s %s glycoprotein' % (tmp_virus,singleletter), '%s %s (%s) protein' % (tmp_virus,protein,singleletter), '%s %s glycoprotein' % (tmp_virus,protein), '%s %s (%s) glycoprotein' % (tmp_virus,protein,singleletter), '(%s) %s protein' % (tmp_virus,protein), '(%s) %s (%s) protein' % (tmp_virus,protein,singleletter), '(%s) %s glycoprotein' % (tmp_virus,protein) , '(%s) %s (%s) glycoprotein' % (tmp_virus,protein,singleletter) ]
			
			ambig_aliases = [ '%s protein' % protein, 'coronavirus %s protein' % protein ]
			
			short_name = '%s_%s' % (virus.replace('-','').lower(),protein.lower())
			long_name = '%s %s protein' % (virus,protein)
			entities[short_name] = {'name':long_name, 'type': 'gene_or_protein', 'associated_virus':virus, 'aliases':aliases, 'ambiguous_aliases': ambig_aliases}
		
	# Oddly, from: https://www.nytimes.com/interactive/2020/04/03/science/coronavirus-genome-bad-news-wrapped-in-protein.html
	sarscov2_proteins = ['ORF1ab','ORF3a','ORF6','ORF7a','ORF8','ORF10'] + [ 'NSP%d' % num for num in range(1,17) if num != 11 ]
	
	for protein in sarscov2_proteins:
		virus = 'SARS-CoV-2'
		virus_names = ['SARS-CoV-2','SARS CoV 2','SARS Coronavirus 2', '2019-nCoV' ]
		if len(protein) == 1:
			aliases = [ '%s %s protein' % (v,protein) for v in virus_names ]
			ambig_aliases = [ '%s protein' % protein ]
		else:
			aliases += [ template % (v,protein) for template in [ '%s %s', '%s %s protein' ] for v in virus_names ]
			ambig_aliases = [ '%s protein' % protein, protein ]
		short_name = 'sarscov2_%s' % protein.lower()
		long_name = 'SARS-CoV-2 %s protein' % protein
		entities[short_name] = {'name':long_name, 'type': 'gene_or_protein', 'associated_virus':virus, 'aliases':aliases, 'ambiguous_aliases': ambig_aliases}
		
	#entities['sarscov_nsp5']['aliases'] += [ template % virus for template in ['%s 3CL(Pro)','%s 3CL Pro ','%s 3CLPro','%s 3C-like protease','%s main proteinase'] for virus in ['SARS-CoV','SARS coronavirus']]
	#entities['sarscov_nsp5']['ambiguous_aliases'] += ['3CL(Pro)','3CL Pro','3CLPro','3C-like protease']
	
	entities['sarscov2_nsp5']['aliases'] += [ template % virus for template in ['%s 3CL(Pro)','%s 3CL Pro ','%s 3CLPro','%s 3C-like protease','%s main proteinase'] for virus in ['SARS-CoV-2','SARS coronavirus 2','2019-nCoV']]
	entities['sarscov2_nsp5']['ambiguous_aliases'] += ['3CL(Pro)','3CL Pro','3CLPro','3C-like protease']
	
	print('Saving JSON file...')
	with open(args.outJSON,'w') as f:
		#entities_as_list = [ entities[entityID] for entityID in sorted(entities.keys()) ]
		json.dump(entities,f,indent=2,sort_keys=True)


