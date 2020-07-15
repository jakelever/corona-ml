import argparse
from collections import Counter
from utils import detect_language
import json

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Check the likely language of each document and filter non-English documents')
	parser.add_argument('--inJSON',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--outJSON',required=True,type=str,help='JSON file with likely English-only documents')
	parser.add_argument('--nonEnglish',required=True,type=str,help='JSON file with languages extracted for non-English documents')
	args = parser.parse_args()

	print("Loading...")
	with open(args.inJSON) as f:
		documents = json.load(f)

	englishDocuments = []
	nonenglishDocuments = []

	print("Filtering...")
	languageCounter = Counter()
	for i,doc in enumerate(documents):
		if (i%1000) == 0:
			print("  Processed %.1f%% (%d/%d)" % (100*i/len(documents),i,len(documents)))
	
		combined_text = doc['title'] + '\n' + doc['abstract']
		
		nonenglish_languages = detect_language(combined_text)
		languageCounter += Counter(nonenglish_languages)
		
		if len(nonenglish_languages) == 0:
			englishDocuments.append(doc)
		else:
			doc['languages'] = nonenglish_languages
			nonenglishDocuments.append(doc)
			
	print("Saving filtered file...")
	with open(args.outJSON,'w') as f:
		json.dump(englishDocuments,f,indent=2,sort_keys=True)
		
	print("Saving report file...")
	with open(args.nonEnglish,'w') as f:
		json.dump(nonenglishDocuments,f,indent=2,sort_keys=True)
		
	print(languageCounter)
	print("Filtered %d documents with non-english language" % len(nonenglishDocuments))
