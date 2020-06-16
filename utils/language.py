import nltk
from nltk.corpus import stopwords
import re

filterREs = None
def prepare():
	global filterREs
	
	english = set(stopwords.words('english') + ['se','sera','et'])
	supported_languages = ['arabic','azerbaijani','danish','dutch','finnish','french','german','greek','hungarian','indonesian','italian','kazakh','nepali','norwegian','portuguese','romanian','russian','slovene','spanish','swedish','tajik','turkish']

	filterWords = {}
	for l in supported_languages:
		filterWords[l] = [ word for word in set(stopwords.words(l)) if not word in english and len(word) >= 2 ]

	#filterWords['french'] = [ word for word in set(stopwords.words('french')) if not word in english and len(word) >= 2 ]
	#filterWords['german'] = [ word for word in set(stopwords.words('german')) if not word in english and len(word) >= 2 ]
	#filterWords['spanish'] = [ word for word in set(stopwords.words('spanish')) if not word in english and len(word) >= 2 ]
	#filterWords['dutch'] = [ word for word in set(stopwords.words('dutch')) if not word in english and len(word) >= 2 ]

	filterREs = {}
	for language,words in filterWords.items():
		filterREs[language] = [ re.compile(r'\s%s\s' % re.escape(word)) for word in words ]
		#print(language, words)

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
				
def detect_language(text):
	global filterREs
	if filterREs is None:
		prepare()
	
	text = text.lower()
	
	found = []
	for language,regexes in filterREs.items():
		matching = [ 1 for regex in regexes if regex.search(text) ]
		if len(matching) >= 5:
			found.append(language)
			
	if any(is_cjk(c) for c in text):
		found.append('cjk')
		
	return found
	
def filter_languages(documents):	
	filtered_cord_uids = set()
	filtered_pubmed_ids = set()
	with open('languageFiltered.tsv') as f:
		for line in f:
			cord_uid,pubmed_id,languages,url = line.strip('\n').split('\t')
			if cord_uid:
				filtered_cord_uids.add(cord_uid)
			if pubmed_id:
				filtered_pubmed_ids.add(pubmed_id)

	documents = [ d for d in documents if not d['cord_uid'] in filtered_cord_uids ]
	documents = [ d for d in documents if not d['pubmed_id'] in filtered_pubmed_ids ]
	
	return documents