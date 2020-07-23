import argparse
from collections import Counter, defaultdict
import json
import string

def remove_punctuation(text):
    exclude = set(string.punctuation)
    return ''.join(ch for ch in text if ch not in exclude)

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Remove duplicate documents')
	parser.add_argument('--inJSON',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--outJSON',required=True,type=str,help='JSON file with fewer documents')
	args = parser.parse_args()

	print("Loading...")
	with open(args.inJSON) as f:
		documents = json.load(f)
		
	print("Loaded %d documents" % len(documents))
		
	print("Finding groupings of duplicate papers...")
	for i,d in enumerate(documents):
		d['group_id'] = i
    
	groupings = defaultdict(list)
	for d in documents:
		groupings[d['group_id']].append(d)

	# These are the different keys that the papers will be merged with
	keys = ['doi','pubmed_id','cord_uid','pmcid',('publish_year','title','authors'),('publish_year','title','abstract'),('publish_year','title','journal')]
	
	for key in keys:
		groupedById = defaultdict(list)
		for d in documents:
			# Assign documents into group based on a key (or keys), e.g. doi
			if isinstance(key,tuple):
				doc_identifier = tuple( remove_punctuation(d[k].lower()) if k in ['title','journal','abstract'] else d[k] for k in key )
				
				if 'title' in key and len(d['title']) < 20:
					continue # Skip short title for being too vague
				if 'abstract' in key and len(d['abstract']) < 50:
					continue # Skip short abstracts for being too vague
					
				if not all(doc_identifier):
					continue
				doc_identifier = str(doc_identifier)
			else:
				doc_identifier = d[key]
				if not doc_identifier:
					continue

			groupedById[doc_identifier].append(d)

		for group in groupedById.values():
			if len(group) > 1:
				group_ids = set([ d['group_id'] for d in group ])
				all_group_members = sum([groupings[gid] for gid in group_ids], [])
				
				new_group_id = min(group_ids)

				# Set all members to have the same group ID
				for d in all_group_members:
					assert 'group_id' in d
					d['group_id'] = new_group_id

				# Delete the old groups and replace with one mega group
				for gid in group_ids:
					del groupings[gid]
				groupings[new_group_id] = all_group_members

	mergeMap = defaultdict(list)
	for d in documents:
		merge_id = d['group_id']
		del d['group_id']
		mergeMap[merge_id].append(d)

	print("Merging documents...")
	merged_documents = []

	for merge_id, docs in mergeMap.items():
		if len(docs) > 1:
			
			# Get all the unique identifiers in all the papers in this group and do some sorting
			dois = sorted(set( d['doi'] for d in docs if d['doi'] ))
			pubmed_ids = sorted(set( d['pubmed_id'] for d in docs if d['pubmed_id'] ))
			pmcids = sorted(set( d['pmcid'] for d in docs if d['pmcid'] ))
			
			urls = sum([ d['url'].split(';') for d in docs if d['url']],[])
			urls = [ url.strip() for url in urls ]
			urls = [ url.rstrip('/') for url in urls if 'www.ncbi.nlm.nih.gov/pubmed/' in url ]
			urls = sorted(set( url for url in urls if url ))
			
			all_ids = {'doi':dois,'pubmed_id':pubmed_ids,'pmcid':pmcids,'url':urls}
			
			# Sort the documents by title then abstract length (so that shorter abstracts get overwritten)
			docs = sorted(docs, key=lambda x:(len(x['title']),len(x['abstract'])))
			
			# Create a single merged document, initially with empty values for each key
			keys = sorted(set(sum([list(d.keys()) for d in docs],[])))
			merged_doc = { k:'' for k in keys }

			# Populate them using 
			for d in docs:
				for k,v in d.items():
					if v:
						merged_doc[k] = v
						
			merged_doc['ids_from_merged_documents'] = all_ids
			merged_documents.append(merged_doc)
		else:
			merged_documents.append(docs[0])
			
	print("Cleaning up URLs...")
	for d in merged_documents:
		if d['pubmed_id']:
			d['url'] = "https://pubmed.ncbi.nlm.nih.gov/%s" % d['pubmed_id']
		elif d['doi']:
			d['url'] = "https://doi.org/%s" % d['doi']
		elif d['pmcid']:
			d['url'] = "https://www.ncbi.nlm.nih.gov/pmc/articles/%s" % d['pmcid']
		elif d['url']:
			urls = [ u.strip() for u in d['url'].split(';') ]
			assert not any('pubmed' in url for url in urls), "Found a document with a Pubmed URL (%d) but no PubMed ID" % str(urls)
			d['url'] = urls[0]
		else:
			d['url'] = None
			    
	print("Removed %d duplicate documents" % (len(documents)-len(merged_documents)))
	
	print("Running final checks to check no duplicate IDs...")
	
	for d in merged_documents:
		assert d['doi'] or d['pubmed_id'] or d['cord_uid'], "Found document that doesn't have a DOI, Pubmed ID or CORD UID"
    
	doiCounter = Counter( d['doi'] for d in merged_documents if d['doi'] )
	multipleDOIs = [ doi for doi,count in doiCounter.items() if count > 1 ]
	assert len(multipleDOIs) == 0, "Found duplicate DOIs: %s" % str(multipleDOIs)

	pmidCounter = Counter( d['pubmed_id'] for d in merged_documents if d['pubmed_id'] )
	multiplePubmedIDs = [ doi for pubmed_id,count in pmidCounter.items() if count > 1 ]
	assert len(multiplePubmedIDs) == 0, "Found duplicate Pubmed IDs: %s" % str(multiplePubmedIDs)

	cordCounter = Counter( d['cord_uid'] for d in merged_documents if d['cord_uid'] )
	multipleCordUIDs = [ doi for cord_uid,count in cordCounter.items() if count > 1 ]
	assert len(multipleCordUIDs) == 0, "Found duplicate CORD UIDs: %s" % str(multipleCordUIDs)
	
	print("Checks PASSED")
	
	print("Saving %d documents to JSON file..." % len(merged_documents))
	with open(args.outJSON,'w') as f:
		json.dump(merged_documents,f,indent=2,sort_keys=True)

	