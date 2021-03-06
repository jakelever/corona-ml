
#import sys
#sys.path.insert(0,'/home/users/jlever/.local/lib/python3.6/site-packages')

import argparse
import json
import os
import sys
from collections import Counter

import ktrain
from transformers import AutoTokenizer, TFAutoModelForSequenceClassification

def main():
	parser = argparse.ArgumentParser('Use the jakelever/coronabert sequence classifier from HuggingFace.co to predict topics/article types')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--prevJSON',type=str,required=False,help='Optional previously processed output (to save time)')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON file with documents')
	args = parser.parse_args()

	print("Loading tokenizer and model...")
	tokenizer = AutoTokenizer.from_pretrained("jakelever/coronabert")
	model = TFAutoModelForSequenceClassification.from_pretrained("jakelever/coronabert")
	model.compile(loss='binary_crossentropy',optimizer='adam', metrics=['accuracy'])

	print("Setting up ktrain...")
	categories = list(model.config.id2label.values())
	preproc = ktrain.text.Transformer('jakelever/coronabert',maxlen=500,class_names=categories)
	preproc.preprocess_train_called = True
	predictor = ktrain.get_predictor(model, preproc)

	print("Loading documents...")

	category_map = {}
	if args.prevJSON and os.path.isfile(args.prevJSON):
		with open(args.prevJSON) as f:
			prev_documents = json.load(f)

		for d in prev_documents:
			category_key = (d['title'],d['abstract'],str(d['annotations']))
			category_map[category_key] = d['categories']

	with open(args.inJSON) as f:
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

	annotated_counts = Counter()
	for d in annotated_docs:
		annotated_categories = [ a for a in d['annotations'] if a in categories ]
		annotated_categories = sorted(set(annotated_categories))
		annotated_counts += Counter(annotated_categories)
		d['categories'] = annotated_categories
	print("Annotated Category Counts in %d documents:" % len(annotated_docs), annotated_counts)


	if len(unannotated_docs) > 0:
		print("Making predictions...")
		unannotated_texts = [ d['title'] + "\n" + d['abstract'] for d in unannotated_docs ]
		predictions = predictor.predict(unannotated_texts)

		assert len(predictions) == len(unannotated_docs)

		predicted_counts = Counter()
		for i,d in enumerate(unannotated_docs):
			predictions_for_doc = predictions[i]
			predicted_categories = [ c for c,p in predictions_for_doc if p > 0.5 ]
			predicted_counts += Counter(predicted_categories)
			d['categories'] = predicted_categories

		print("Predicted Category Counts in %d documents:" % len(unannotated_docs), predicted_counts)

	output_documents = already_done + needs_doing

	print("Saving %d documents..." % len(output_documents))
	with open(args.outJSON,'w') as f:
		json.dump(output_documents,f,indent=2,sort_keys=True)

	print("Done")

if __name__ == '__main__':
	main()
	
