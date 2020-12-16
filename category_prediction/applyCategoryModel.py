
import sys
sys.path.insert(0,'/home/users/jlever/.local/lib/python3.6/site-packages')

import pickle
import argparse
import json
import re
import os
import sys
from collections import Counter,defaultdict
from coronacode import DocumentClassifier

def main():
	parser = argparse.ArgumentParser('Build a model for a classifier')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--modelDir',required=True,type=str,help='Directory of model data')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON file with documents')
	args = parser.parse_args()

	with open(args.inJSON) as f:
		documents = json.load(f)

	for d in documents:
		d['categories'] = []

	annotated_docs = [ d for d in documents if len(d['annotations']) > 0 ]
	unannotated_docs = [ d for d in documents if len(d['annotations']) == 0 ]

	print("%d annotated_docs and %d unannotated_docs" % (len(annotated_docs),len(unannotated_docs)))

	categories_file = os.path.join(args.modelDir,'categories.json')
	with open(categories_file) as f:
		categories = json.load(f)

	annotated_label_count, predicted_label_count = 0,0

	annotated_counts = Counter()
	for d in annotated_docs:
		annotated_categories = [ a for a in d['annotations'] if a in categories ]
		annotated_categories = sorted(set(annotated_categories))
		annotated_counts += Counter(annotated_categories)
		d['categories'] = annotated_categories
	print("Annotated Category Counts:", annotated_counts)

	print("Loading model...")
	clf = DocumentClassifier.load(args.modelDir)

	print("Making predictions...")
	predictions = clf.predict(unannotated_docs)

	assert predictions.shape[0] == len(unannotated_docs)
	assert predictions.shape[1] == len(categories)

	predicted_counts = Counter()
	for i,d in enumerate(unannotated_docs):
		predictions_for_doc = predictions[i,:]
		predicted_categories = [ c for p,c in zip(predictions_for_doc,categories) if p ]
		predicted_counts += Counter(predicted_categories)
		d['categories'] = predicted_categories

	print("Predicted Category Counts:", predicted_counts)

	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)

	print("Done")

if __name__ == '__main__':
	main()
	
