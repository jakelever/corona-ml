import kindred
import argparse
import pickle
import json
import os
import sys

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Parse a set of documents and save a pickled form')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--prevPickle',required=False,type=str,help='A previous pickled parse file to pull previous parses from')
	parser.add_argument('--outPickle',required=True,type=str,help='Pickle of parsed documents')
	args = parser.parse_args()
	
	use_previous_parses = (args.prevPickle and os.path.isfile(args.prevPickle))
	
	print("Loading documents...")
	sys.stdout.flush()
	with open(args.inJSON) as f:
		documents = json.load(f)
		
	existing_mapping = {}
	if use_previous_parses:
		print("Loading previous parses for reuse...")
		sys.stdout.flush()
		with open(args.prevPickle,'rb') as f:
			previously_parsed_corpus = pickle.load(f)
			
		print("Setting up lookup for previous parses...")
		sys.stdout.flush()
		for kindred_doc in previously_parsed_corpus.documents:
			identifier = kindred_doc.text
			existing_mapping[identifier] = kindred_doc
	
	print("Checking which documents need to be parsed...")
	sys.stdout.flush()
	needs_parsing,already_parsed = [],[]
	for doc in documents:
		title_plus_abstract = doc['title'] + "\n" + doc['abstract']
		if title_plus_abstract in existing_mapping:
			already_parsed.append(existing_mapping[title_plus_abstract])
		else:
			needs_parsing.append(title_plus_abstract)		
	needs_parsing = sorted(set(needs_parsing))
	
	if use_previous_parses:
		print("Found %d documents with existing parses" % len(already_parsed))
	print("Found %d documents to parse" % len(needs_parsing))
	sys.stdout.flush()
	
	corpus = kindred.Corpus()
	for title_plus_abstract in needs_parsing:
		kindred_doc = kindred.Document(title_plus_abstract)
		corpus.addDocument(kindred_doc)
		
	print("Parsing...")
	sys.stdout.flush()
	parser = kindred.Parser(model='en_core_sci_sm')
	parser.parse(corpus)
	
	corpus.documents += already_parsed
	
	print("Saving %d parses..." % len(corpus.documents))
	sys.stdout.flush()
	with open(args.outPickle,'wb') as outF:
		pickle.dump(corpus,outF)

	
	
	