
import sys
import argparse
import json
import os
import sys
from collections import Counter
from coronacode import DocumentClassifier
import gzip

def main():
	parser = argparse.ArgumentParser('Build a model for a classifier')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--prevJSON',type=str,required=False,help='Optional previously processed output (to save time)')
	parser.add_argument('--modelDir',required=True,type=str,help='Directory of model data')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON file with documents')
	args = parser.parse_args()

	category_map = {}
	if args.prevJSON and os.path.isfile(args.prevJSON):
		with gzip.open(args.prevJSON,'rt') as f:
			prev_documents = json.load(f)

		for d in prev_documents:
			category_key = (d['title'],d['abstract'],str(d['annotations']))
			category_map[category_key] = d['categories']

	with gzip.open(args.inJSON,'rt') as f:
		documents = json.load(f)

	needs_doing = []
	already_done = []
	for d in documents:
		if not 'annotations' in d:
			d['annotations'] = []

		category_key = (d['title'],d['abstract'],str(d['annotations']))
		if category_key in category_map:
			d['categories'] = category_map[category_key]
			already_done.append(d)
		else:
			needs_doing.append(d)

	print("%d documents previously processed" % len(already_done))
	print("%d documents to be processed" % len(needs_doing))
	print()

	for d in needs_doing:
		d['categories'] = []

	annotated_docs = [ d for d in needs_doing if len(d['annotations']) > 0 ]
	unannotated_docs = [ d for d in needs_doing if len(d['annotations']) == 0 ]

	print("%d annotated_docs and %d unannotated_docs in documents to process" % (len(annotated_docs),len(unannotated_docs)))

	categories_file = os.path.join(args.modelDir,'categories.json')
	with open(categories_file) as f:
		categories = json.load(f)

	annotated_counts = Counter()
	for d in annotated_docs:
		annotated_categories = [ a for a in d['annotations'] if a in categories ]
		annotated_categories = sorted(set(annotated_categories))
		annotated_counts += Counter(annotated_categories)
		d['categories'] = annotated_categories
	print("Annotated Category Counts in %d documents:" % len(annotated_docs), annotated_counts)

	if len(unannotated_docs) > 0:
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

		print("Predicted Category Counts in %d documents:" % len(unannotated_docs), predicted_counts)

	output_documents = already_done + needs_doing

	print("Saving %d documents..." % len(output_documents))
	with gzip.open(args.outJSON,'wt') as f:
		json.dump(output_documents,f,indent=2,sort_keys=True)

	print("Done")

if __name__ == '__main__':
	main()
	
