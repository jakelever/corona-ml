import kindred
import argparse
import pickle
from utils import load_documents

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Parse a set of documents and save a pickled form')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--outPickle',required=True,type=str,help='Pickle of parsed documents')
	args = parser.parse_args()
	
	print("Loading...")
	documents = load_documents(args.inJSON)
	
	corpus = kindred.Corpus()
	for doc in documents:
		kindred_doc = kindred.Document(doc['title'] + "\n" + doc['abstract'])
		kindred_doc.metadata['url'] = doc['url']
		kindred_doc.metadata['title'] = doc['title']
		kindred_doc.metadata['cord_uid'] = doc['cord_uid']
		kindred_doc.metadata['pubmed_id'] = doc['pubmed_id']
		kindred_doc.metadata['doi'] = doc['doi']
		corpus.addDocument(kindred_doc)
		#break
		
	print("Parsing...")
	parser = kindred.Parser(model='en_core_sci_sm')
	parser.parse(corpus)
	
	print("Saving...")
	with open(args.outPickle,'wb') as outF:
		pickle.dump(corpus,outF)

	print(len(corpus.documents))
	
	
	