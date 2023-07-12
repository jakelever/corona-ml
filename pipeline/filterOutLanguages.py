import argparse
from collections import Counter,defaultdict
import json
import os
import time
import sys

from nltk.corpus import stopwords
import re
from multiprocessing import Pool
import gzip

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
	assert filterREs is not None

	text = text.lower()
	
	found = []
	for language,regexes in filterREs.items():
		matching = [ 1 for regex in regexes if regex.search(text) ]
		if len(matching) >= 5:
			found.append(language)
			
	if any(is_cjk(c) for c in text):
		found.append('cjk')
		
	return found
	
def processDoc(doc):
	combined_text = doc['title'] + '\n' + doc['abstract']
		
	nonenglish_languages = detect_language(combined_text)
	
	if len(nonenglish_languages) == 0:
		return ['english']
	else:
		return nonenglish_languages

def main():
	parser = argparse.ArgumentParser('Check the likely language of each document and filter non-English documents')
	parser.add_argument('--inJSON',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--prevEnglishDocs',required=False,type=str,help='JSON file with previously processed likely English-only documents')
	parser.add_argument('--prevNonEnglishDocs',required=False,type=str,help='JSON file with previously processed likely non-English documents')
	parser.add_argument('--outEnglishDocs',required=True,type=str,help='JSON file with likely English-only documents')
	parser.add_argument('--outNonEnglishDocs',required=True,type=str,help='JSON file with languages extracted for non-English documents')
	args = parser.parse_args()
	
	keys = ['title','abstract']

	prepare()
	
	print("Loading...")
	with gzip.open(args.inJSON,'rt') as f:
		documents = json.load(f)
		
	documentsByIdentifier = defaultdict(lambda : None)
	for doc in documents:
		identifier = tuple([ doc[k] for k in keys ])
		documentsByIdentifier[identifier] = doc
		
	prev_results = {}
	if args.prevEnglishDocs and args.prevNonEnglishDocs and os.path.isfile(args.prevEnglishDocs) and os.path.isfile(args.prevNonEnglishDocs):
		print("Reusing old language assignments where possible...")
		with open(args.prevEnglishDocs,'r') as f:
			englishDocuments = json.load(f)
		with open(args.prevNonEnglishDocs,'r') as f:
			nonenglishDocuments = json.load(f)

		for doc in englishDocuments + nonenglishDocuments:
			identifier = tuple( doc[k] for k in keys )
			prev_results[identifier] = doc['languages']
		
		print("Found %d existing language assignments" % len(prev_results))

	needs_processing = []
	for doc in documents:
		identifier = tuple([ doc[k] for k in keys ])
		if not identifier in prev_results:
			needs_processing.append(doc)
			
	print("Found %d documents to process" % len(needs_processing))

	print("Filtering...")

	if len(needs_processing) > 0:
		with Pool(5) as pool:
			new_results = [ pool.apply_async(processDoc, (doc,)) for doc in needs_processing ]
			while True:
				num_completed = len( [ r for r in new_results if r.ready() ] )
				todo = len(needs_processing) - num_completed

				print("  Processed %.1f%% (%d/%d)" % (100*num_completed/len(needs_processing),num_completed,len(needs_processing)))
				sys.stdout.flush()
				if todo == 0:
					break
				time.sleep(5)

			new_results = [ r.get() for r in new_results ]

		for doc,new_result in zip(needs_processing,new_results):
			identifier = tuple([ doc[k] for k in keys ])
			prev_results[identifier] = new_result
		
	englishDocuments, nonenglishDocuments = [], []
	for doc in documents:
	
		identifier = tuple([ doc[k] for k in keys ])
		doc['languages'] = prev_results[identifier]
		
		if doc['languages'] == ['english']:
			englishDocuments.append(doc)
		else:
			nonenglishDocuments.append(doc)
			
	print("Saving file with %d English documents..." % len(englishDocuments))
	with gzip.open(args.outEnglishDocs,'wt') as f:
		json.dump(englishDocuments,f,indent=2,sort_keys=True)
		
	print("Saving file with %d non-English documents..." % len(nonenglishDocuments))
	with gzip.open(args.outNonEnglishDocs,'wt') as f:
		json.dump(nonenglishDocuments,f,indent=2,sort_keys=True)
		
	languageCounter = Counter(lang for doc in nonenglishDocuments for lang in doc['languages'])
	print("Languages found in %d non-English documents: %s" % (len(nonenglishDocuments),str(languageCounter)))

if __name__ == '__main__':
	main()

