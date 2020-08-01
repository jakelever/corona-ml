import json
import argparse
import string
import calendar
import re
from datetime import date

def remove_punctuation(text):
	exclude = set(string.punctuation)
	return ''.join(ch for ch in text if ch not in exclude)

def cleanup_documents(documents):
	dashCharacters = ["-", "\u00ad", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2043", "\u2053"]

	empty_abstracts = {'','this article has no abstract','no abstract is available for this article','letter without abstract','unknown','not available','no abstract available','na','no abstract provided','no abstract','none','abstract','letter without abstract','not availble','null','graphical abstract'}
	max_empty_abstract_length = max(map(len,empty_abstracts))

	title_prefixes_to_trim = ['full-length title', 'infographic title', 'complete title', 'original title', 'title']
	abstract_prefixes_to_trim = ['accepted 7 july 2020abstract', 'physicians abstracts', 'unlabelled abstract', 'structured abstract', 'original abstracts', 'summary/abstract', 'original abstract', 'abstracts', ']abstract', 'abstract']

	preprintRemapping = {}
	preprintRemapping['medrxiv'] = 'medRxiv'
	preprintRemapping['medrxiv.org'] = 'medRxiv'
	preprintRemapping['medrxiv : the preprint server for health sciences'] = 'medRxiv'
	preprintRemapping['biorxiv'] = 'bioRxiv'
	preprintRemapping['biorxiv.org'] = 'bioRxiv'
	preprintRemapping['biorxiv : the preprint server for biology'] = 'bioRxiv'
	preprintRemapping['chemrxiv'] = 'ChemRxiv'
	preprintRemapping['chemrxiv.org'] = 'ChemRxiv'
	preprintRemapping['chemrxiv : the preprint server for chemistry'] = 'ChemRxiv'
	preprintRemapping['arxiv'] = 'arXiv'
	preprintRemapping['arxiv.org'] = 'arXiv'
	preprintRemapping['arxiv.org e-print archive'] = 'arXiv'
	
	colonWithNoSpaceRegex = re.compile('(introduction|background|method|methods|result|results|findings|discussion|conclusion|conclusions|evidence|objective|objectives|abbreviations|funding|):(\S)',flags=re.IGNORECASE)

	for doc in documents:
		doc['title'] = doc['title'].strip()
		doc['abstract'] = doc['abstract'].strip()

		if any (dc in doc['title'] for dc in dashCharacters):
			for dc in dashCharacters:
				doc['title'] = doc['title'].replace(dc,'-')
		if any (dc in doc['abstract'] for dc in dashCharacters):
			for dc in dashCharacters:
				doc['abstract'] = doc['abstract'].replace(dc,'-')

		abstract_no_punct = remove_punctuation(doc['abstract'].lower())
		if abstract_no_punct in empty_abstracts:
			doc['abstract'] = ''

		for prefix in title_prefixes_to_trim:
			if doc['title'].lower().startswith(prefix):
				doc['title'] = doc['title'][len(prefix):].lstrip(': ').strip()
		for prefix in abstract_prefixes_to_trim:
			if doc['abstract'].lower().startswith(prefix):
				doc['abstract'] = doc['abstract'][len(prefix):].lstrip(': ').strip()
				
		if doc['title'].startswith('[') and (doc['title'].endswith(']') or doc['title'].endswith('].')):
			doc['title'] = doc['title'].lstrip('[').rstrip('.').rstrip(']')
				
		# Cleanup some messy section headings in the abstract where there is
		# no space after a colon.
		doc['abstract'] = colonWithNoSpaceRegex.sub('\\1: \\2',doc['abstract'])

		if 'source_x' in doc and doc['source_x'].lower() in ['biorxiv','medrxiv','arxiv']:
			doc['journal'] = doc['source_x']

		journal_lower = doc['journal'].lower()
		if journal_lower in preprintRemapping:
			doc['journal'] = preprintRemapping[journal_lower]

		if 'publish_time' in doc:
			assert len(doc['publish_time']) in [0,4,10], doc['publish_time']
			doc['publish_year'] = None
			doc['publish_month'] = None
			doc['publish_day'] = None
			if len(doc['publish_time']) == 4:
				doc['publish_year'] = doc['publish_time']
			elif len(doc['publish_time']) == 10:
				doc['publish_year'] = doc['publish_time'][0:4]
				doc['publish_month'] = doc['publish_time'][5:7]
				doc['publish_day'] = doc['publish_time'][8:10]
			del doc['publish_time']

		if isinstance(doc['publish_year'],str):
			doc['publish_year'] = doc['publish_year'].strip()
		if isinstance(doc['publish_month'],str):
			doc['publish_month'] = doc['publish_month'].strip()
		if isinstance(doc['publish_day'],str):
			doc['publish_day'] = doc['publish_day'].strip()

		date_status = (bool(doc['publish_year']),bool(doc['publish_month']),bool(doc['publish_day']))
		assert date_status in [(True,True,True),(True,True,False),(True,False,False),(False,False,False)]

		if doc['publish_year']:
			doc['publish_year'] = int(doc['publish_year'])
			assert doc['publish_year'] > 1700 and doc['publish_year'] < 2100
		else:
			doc['publish_year'] = None

		if doc['publish_month']:
			doc['publish_month'] = int(doc['publish_month'])
			assert doc['publish_month'] >= 1 and doc['publish_month'] <= 12
		else:
			doc['publish_month'] = None

		if doc['publish_day']:
			doc['publish_day'] = int(doc['publish_day'])
			_,days_in_month = calendar.monthrange(doc['publish_year'],doc['publish_month'])
			assert doc['publish_day'] >= 1 and doc['publish_day'] <= days_in_month
		else:
			doc['publish_day'] = None

		# Check the publication isn't in the future, and drop it back to this month if it appears to be
		if doc['publish_year'] is not None:
			pub_date = date(doc['publish_year'],doc['publish_month'] if doc['publish_month'] else 1,doc['publish_day'] if doc['publish_day'] else 1)
			if pub_date > date.today():
				doc['publish_year'] = date.today().year
				doc['publish_month'] = doc['publish_month'] if doc['publish_month'] == date.today().month else None
				doc['publish_day'] = None

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Integrate in metadata from web scraping')
	parser.add_argument('--inJSON',required=True,type=str,help='Input JSON documents')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with added metadata')
	args = parser.parse_args()
	
	print("Loading documents...")
	with open(args.inJSON) as f:
		documents = json.load(f)
		
	print("Cleaning documents...")
	cleanup_documents(documents)
		
	print("Saving data...")
	with open(args.outJSON,'w',encoding='utf8') as f:
		json.dump(documents,f)