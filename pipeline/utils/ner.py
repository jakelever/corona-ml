import re
from collections import defaultdict

def tag_entities(text,lookup):
	assert isinstance(text,str)
	assert isinstance(lookup,dict) or isinstance(lookup,defaultdict)

	regex = re.compile(r"\b\S+?\b")

	# Find the max length (# of tokens) in the lookup table
	max_length = max(len(list(regex.finditer(k))) for k in lookup.keys())
	
	# Simple tokenize
	token_locations = [(m.start(),m.end()) for m in regex.finditer(text) ]

	found = []
	for length in range(min(max_length,len(token_locations)),0,-1):
		for start_token_index in range(0,len(token_locations)-length+1):
			end_token_index = start_token_index + length - 1
			start_token_start = token_locations[start_token_index][0]
			end_token_end = token_locations[end_token_index][1]

			substring = text[start_token_start:end_token_end]
			substring_lower = substring.lower()

			if substring_lower in lookup:
				for entity_type,entity_id,entity_normalized in lookup[substring_lower]:
					entity = {'start':start_token_start,'end':end_token_end,'id':entity_id,'type':entity_type,'text':substring,'normalized':entity_normalized,}
					found.append(entity)

				text = text[:start_token_start] + "#"*len(substring) + text[end_token_end:]

	return found

def tag_documents(documents,lookup):
	for d in documents:
		if not 'entities' in d:
			d['entities'] = []
		
		for section in ['title','abstract']:
			for entity in tag_entities(d[section],lookup):
				entity['section'] = section
				d['entities'].append(entity)
				
		# Do an awkward unique on the list of dictionaries
		#d['entities'] = [dict(s) for s in set(frozenset(d.items()) for d in )]
		d['entities'] = list(map(dict, set(tuple(sorted(e.items())) for e in d['entities'])))

