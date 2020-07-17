import kindred
import argparse
import pickle
import json
import os

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Parse a set of documents and save a pickled form')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--prevPickle',required=False,type=str,help='A previous pickled parse file to pull previous parses from')
	parser.add_argument('--outPickle',required=True,type=str,help='Pickle of parsed documents')
	args = parser.parse_args()
	
	keys = ['title','cord_uid','pubmed_id','doi']
	
	use_previous_parses = (args.prevPickle and os.path.isfile(args.prevPickle))
	
	existing_mapping = {}
	if use_previous_parses:
		with open(args.prevPickle,'rb') as f:
			previously_parsed_corpus = pickle.load(f)
			
		for kindred_doc in previously_parsed_corpus.documents:
			identifier = tuple([ kindred_doc.metadata[k] for k in keys ])
			existing_mapping[identifier] = kindred_doc
	
	print("Loading...")
	with open(args.inJSON) as f:
		documents = json.load(f)
		
	needs_parsing,already_parsed = [],[]
	for doc in documents:
		identifier = tuple([ doc[k] for k in keys ])
		if identifier in existing_mapping:
			already_parsed.append(existing_mapping[identifier])
		else:
			needs_parsing.append(doc)
			
	if use_previous_parses:
		print("Found %d documents with existing parses" % len(already_parsed))
	print("Found %d documents to parse" % len(needs_parsing))
	
	corpus = kindred.Corpus()
	for doc in needs_parsing:
		kindred_doc = kindred.Document(doc['title'] + "\n" + doc['abstract'])
		
		for k in keys:
			kindred_doc.metadata[k] = doc[k]
		corpus.addDocument(kindred_doc)
		#break
		
	print("Parsing...")
	parser = kindred.Parser(model='en_core_sci_sm')
	parser.parse(corpus)
	
	corpus.documents += already_parsed
	
	print("Saving...")
	with open(args.outPickle,'wb') as outF:
		pickle.dump(corpus,outF)

	print(len(corpus.documents))
	
	
	