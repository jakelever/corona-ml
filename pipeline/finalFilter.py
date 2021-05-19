import argparse
import json
import os
from collections import defaultdict

def main():
	parser = argparse.ArgumentParser('Clean up the associated URLs in documents and remove ones without usable URLs')
	parser.add_argument('--inJSON',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--outJSON',required=True,type=str,help='JSON file with fewer documents')
	args = parser.parse_args()

	print("Loading...")
	with open(args.inJSON) as f:
		documents = json.load(f)
		
	filtered = documents
	if os.path.isfile('checks.json'):
		with open('checks.json') as f:
			checks = json.load(f)
			
		filtered = [ d for d in filtered if not d['doi'] in checks ]
	
	print("%d documents before final filtering" % len(filtered))
	
	filtered = [ d for d in filtered if not d['url'] is None ]
	
	print("%d documents after removing those without a usable URL" % len(filtered))
	
	filtered = [ d for d in filtered if not ('NotRelevant' in d['annotations'] or 'RemoveFromCorpus?' in d['annotations']) ]
	print("%d documents after removing that are manually flagged for removal" % len(filtered))

	print("Combining variants and viral lineages into entities...")
	for d in documents:
		d['entities'] += d['variants']
		d['entities'] += d['viral_lineages']
		del d['variants']
		del d['viral_lineages']

	print("Doing a final check on entities (that names and IDs are unique)")
	entity_normalized_to_id = defaultdict(set)
	entity_id_to_normalized = defaultdict(set)
	for d in documents:
		for e in d['entities']:
			entity_normalized_to_id[e['normalized']].add(e['id'])
			entity_id_to_normalized[e['id']].add(e['normalized'])

	#for e_normalized in entity_normalized_to_id:
	#	assert len(entity_normalized_to_id[e_normalized]) == 1, "Found multiple mappings from normalized name (%s) to ids (%s)" % (e_normalized, entity_normalized_to_id[e_normalized])
	#for e_id in entity_id_to_normalized:
	#	assert len(entity_id_to_normalized[e_id]) == 1, "Found multiple mappings from id (%s) to normalized names (%s)" % (e_id, entity_id_to_normalized[e_id])
	
	print("Cleaning up...")
	for d in documents:
		if 'web_articletypes' in d:
			del d['web_articletypes']
			
		if 'webmetadata' in d:
			del d['webmetadata']
			
	output_fields = ['pubmed_id', 'pmcid', 'doi', 'cord_uid', 'url', 'journal', 'publish_year', 'publish_month', 'publish_day', 'title', 'abstract', 'is_preprint', 'topics', 'articletypes', 'entities']
	print("Checking final output fields...")
	print("Only the following are output for each document: %s" % output_fields)
	
	for i in range(len(filtered)):
		d = filtered[i]
		
		missing_fields = [ k for k in output_fields if not k in d ]
		assert len(missing_fields) == 0, "Document missing expected field(s): %s" % missing_fields
		
		d = { k:d[k] for k in output_fields }
		
		filtered[i] = d
			
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(filtered,f,indent=2,sort_keys=True)
	
if __name__ == '__main__':
	main()

