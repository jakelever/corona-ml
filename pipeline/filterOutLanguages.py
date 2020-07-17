import argparse
from collections import Counter,defaultdict
from utils import detect_language
import json
import os
import time
import ray

@ray.remote
def processDoc(doc):
	combined_text = doc['title'] + '\n' + doc['abstract']
		
	nonenglish_languages = detect_language(combined_text)
	
	return nonenglish_languages

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Check the likely language of each document and filter non-English documents')
	parser.add_argument('--inJSON',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--prevEnglishDocs',required=False,type=str,help='JSON file with previously processed likely English-only documents')
	parser.add_argument('--prevNonEnglishDocs',required=False,type=str,help='JSON file with previously processed likely non-English documents')
	parser.add_argument('--outEnglishDocs',required=True,type=str,help='JSON file with likely English-only documents')
	parser.add_argument('--outNonEnglishDocs',required=True,type=str,help='JSON file with languages extracted for non-English documents')
	args = parser.parse_args()
	
	ray.init()
	
	keys = ['title','cord_uid','pubmed_id','doi']
	
	print("Loading...")
	with open(args.inJSON) as f:
		documents = json.load(f)
		
	documentsByIdentifier = defaultdict(lambda : None)
	for doc in documents:
		identifier = tuple([ doc[k] for k in keys ])
		documentsByIdentifier[identifier] = doc
		
	print(args.prevEnglishDocs, os.path.isfile(args.prevEnglishDocs))
	print(args.prevNonEnglishDocs, os.path.isfile(args.prevNonEnglishDocs))
		
	alreadySeen = set()
	englishDocuments = []
	nonenglishDocuments = []
	if args.prevEnglishDocs and args.prevNonEnglishDocs and os.path.isfile(args.prevEnglishDocs) and os.path.isfile(args.prevNonEnglishDocs):
		print("Reusing old language assignments where possible...")
		with open(args.prevEnglishDocs,'r') as f:
			englishDocuments = json.load(f)
		with open(args.prevNonEnglishDocs,'r') as f:
			nonenglishDocuments = json.load(f)
			prevLanguages = { tuple([ doc[k] for k in keys ]):doc['languages'] for doc in nonenglishDocuments }
			
		print("Pulling the latest version of documents from the new file (assuming the language hasn't changed)...")
		englishDocuments = [ documentsByIdentifier[tuple([ doc[k] for k in keys ])] for doc in englishDocuments ]
		nonenglishDocuments = [ documentsByIdentifier[tuple([ doc[k] for k in keys ])] for doc in nonenglishDocuments ]
		
		englishDocuments = [ doc for doc in englishDocuments if doc is not None ]
		nonenglishDocuments = [ doc for doc in nonenglishDocuments if doc is not None ]
		
		for doc in nonenglishDocuments:
			key = tuple([ doc[k] for k in keys ])
			doc['language'] = prevLanguages[key]

		print("  Loaded %d English documents with matching identifiers to new documents" % len(englishDocuments))
		print("  Loaded %d non-English documents with matching identifiers to new documents" % len(nonenglishDocuments))
			
		for doc in englishDocuments + nonenglishDocuments:
			identifier = tuple([ doc[k] for k in keys ])
			alreadySeen.add(identifier)
		print("Found %d existing language assignments" % len(alreadySeen))

	needs_processing = []
	for doc in documents:
		identifier = tuple([ doc[k] for k in keys ])
		if not identifier in alreadySeen:
			needs_processing.append(doc)
			
	#needs_processing = needs_processing[:100]
	print("Found %d documents to process" % len(needs_processing))

	print("Filtering...")
	results = [ processDoc.remote(doc) for doc in needs_processing ]
	
	if len(results) > 0:
		while True:
			done,todo = ray.wait(results,len(needs_processing),timeout=1)
			print("  Processed %.1f%% (%d/%d)" % (100*len(done)/len(needs_processing),len(done),len(needs_processing)))
			if len(todo) == 0:
				break
			time.sleep(5)
	results = ray.get(results)
	
	for i,doc in enumerate(needs_processing):
		#if (i%1000) == 0:
		#	print("  Processed %.1f%% (%d/%d)" % (100*i/len(needs_processing),i,len(needs_processing)))
	
		nonenglish_languages = results[i]
		#languageCounter += Counter(nonenglish_languages)
		
		if len(nonenglish_languages) == 0:
			englishDocuments.append(doc)
		else:
			doc['languages'] = nonenglish_languages
			nonenglishDocuments.append(doc)
			
	print("Saving file with %d English documents..." % len(englishDocuments))
	with open(args.outEnglishDocs,'w') as f:
		json.dump(englishDocuments,f,indent=2,sort_keys=True)
		
	print("Saving file with %d non-English documents..." % len(nonenglishDocuments))
	with open(args.outNonEnglishDocs,'w') as f:
		json.dump(nonenglishDocuments,f,indent=2,sort_keys=True)
		
	languageCounter = Counter(lang for doc in nonenglishDocuments for lang in doc['languages'])
	print(languageCounter)
	print("Filtered %d documents with non-english language" % len(nonenglishDocuments))
