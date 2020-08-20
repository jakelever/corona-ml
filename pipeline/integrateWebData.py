import argparse
import json
from collections import Counter,defaultdict
import re

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text).strip()
	
def is_cjk(character):
	""""
	Checks whether character is CJK.

		>>> is_cjk(u'\u33fe')
		True
		>>> is_cjk(u'\uFE5F')
		False

	:param character: The character that needs to be checked.
	:type character: char
	:return: bool
	"""
	return any([start <= ord(character) <= end for start, end in 
				[(4352, 4607), (11904, 42191), (43072, 43135), (44032, 55215), 
				 (63744, 64255), (65072, 65103), (65381, 65500), 
				 (131072, 196607)]
				])

def is_cjk_string(text):
	return any(is_cjk(ch) for ch in text)

dashCharacters = ["-", "\u00ad", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2043", "\u2053"]
def cleanup_dashes(list_of_text):
	new_list = []
	for item in list_of_text:
		for dc in dashCharacters:
			item = item.replace(dc,'-')
		new_list.append(item)
	return new_list

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Integrate in metadata from web scraping')
	parser.add_argument('--inJSON',required=True,type=str,help='Input JSON documents')
	parser.add_argument('--webmetadata',required=True,type=str,help='Scraped web data')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with added metadata')
	args = parser.parse_args()
	
	print("Loading documents...")
	with open(args.inJSON) as f:
		documents = json.load(f)
	
	print("Loading webdata...")
	with open(args.webmetadata) as f:
		webmetadata = json.load(f)
		
		
	journalFields = ['citation_journal_title', 'journal', 'journalName', 'journal_title', 'wkhealth_journal_title']
		
	for d in documents:
		urls = []
		if d['doi']:
			urls.append('https://doi.org/%s' % d['doi'])
		if d['url']:
			urls.append(d['url'])
			
		m = {}
		for url in urls:
			if url in webmetadata:
				m.update(webmetadata[url])
				
		m = { k:cleanup_dashes(vals) if isinstance(vals,list) else vals for k,vals in m.items() }
				
		d['webmetadata'] = defaultdict(list,m)
		
	print("Normalizing journal names using web data...")
	
	journal_fields = ['citation_journal_title', 'journal_title', 'journal', 'journalName', 'wkhealth_journal_title']

	skip_journal_list = ['arxiv','medrxiv','biorxiv','chemrxiv']
	
	journal_mapping = defaultdict(list)
	for d in documents:
		if any(skip_journal in d['journal'].lower() for skip_journal in skip_journal_list):
			continue
		
		wm_journals = sum([ d['webmetadata'][f] for f in journal_fields ], [])
		wm_journals = [ j for j in wm_journals if not is_cjk_string(j) ]
		if len(d['journal']) > 3 and wm_journals:
			d['wm_journal'] = wm_journals[0]
			journal_mapping[d['journal'].lower()].append(wm_journals[0])

	journal_mapping = { j:Counter(names).most_common(1)[0][0] for j,names in journal_mapping.items() if names }

	for d in documents:
		if 'wm_journal' in d:
			d['journal'] = d['wm_journal']
			del d['wm_journal']
		elif d['journal'] and d['journal'].lower() in journal_mapping:
			d['journal'] = journal_mapping[d['journal'].lower()]
		
	print("Finding abstracts for documents without abstracts...")
	
	abstract_fields = ['Abstract', 'DC.Description.Abstract', 'DC.abstract', 'abstract', 'citation_abstract', 'eprints.abstract']

	added_abstract_count = 0
	for d in documents:
		if d['abstract'] == '':
			candidate_abstracts = sum([ d['webmetadata'][f] for f in abstract_fields ], [])
			candidate_abstracts = [ remove_html_tags(ca) for ca in candidate_abstracts ]
			candidate_abstracts = [ ca for ca in candidate_abstracts if not ca.startswith('//') ]
			candidate_abstracts = [ ca for ca in candidate_abstracts if len(ca) > 100 ]
			candidate_abstracts = [ ca for ca in candidate_abstracts if not is_cjk_string(ca) ]
			
			candidate_abstracts = sorted(set(candidate_abstracts), key=lambda x: len(x), reverse=True)
			if candidate_abstracts:
				d['abstract'] = candidate_abstracts[0]
				added_abstract_count += 1
				
	print("Added %d new abstracts using web data" % added_abstract_count)
		
	print("Saving data...")
	with open(args.outJSON,'w',encoding='utf8') as f:
		json.dump(documents,f)