
import sys
sys.path.insert(0,'/home/users/jlever/.local/lib/python3.6/site-packages')

sys.path.append('/home/groups/rbaltman/jlever/corona-ml/pipeline')

import pickle
import argparse
import json
import re
import os
import sys
from collections import Counter,defaultdict
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer

import sklearn.metrics 

from coronacode import DocumentClassifier


def main():
	parser = argparse.ArgumentParser('Build a model for a classifier')
	parser.add_argument('--categoriesFile',required=True,type=str,help='Category list file')
	parser.add_argument('--params',required=True,type=str,help='JSON string with parameters')
	parser.add_argument('--useTestSet',action='store_true',help='Whether to use the test set instead of the validation set')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	args = parser.parse_args()

	print("Running with --params %s" % args.params)

	params = json.loads(args.params)

	with open(args.inJSON) as f:
		documents = json.load(f)

	with open(args.categoriesFile) as f:
		categories = [ line.strip() for line in f ]


	#test_docs = [ d for d in documents if 'phase4' in d['annotations'] ]
	#documents = [ d for d in documents if not 'phase4' in d['annotations'] ]

	#viruses = {'SARS-CoV-2','SARS-CoV','MERS-CoV'}
	#documents = [ d for d in documents if any(entity['type'] == 'Virus' for entity in d['entities']) or any( v in d['annotations'] for v in viruses) ]

	train_docs = [ d for d in documents if len(d['annotations']) > 0 and not 'phase4' in d['annotations'] ]
	test_docs = [ d for d in documents if 'phase4' in d['annotations'] ]
	#other_docs = [ d for d in documents if len(d['annotations']) == 0 ]

	toRemoveFromTraining = {'RemoveFromCorpus?','NotAllEnglish','NotRelevant','Skip','Maybe','FixAbstract'}
	train_docs = [ d for d in train_docs if not any (f in d['annotations'] for f in toRemoveFromTraining) ]
	test_docs = [ d for d in test_docs if not any (f in d['annotations'] for f in toRemoveFromTraining) ]

	if not args.useTestSet:
		train_docs, test_docs = train_test_split(train_docs, test_size=0.25, random_state=42)

	train_categories = [ [ a for a in d['annotations'] if a in categories ] for d in train_docs ]
	test_categories = [ [ a for a in d['annotations'] if a in categories ] for d in test_docs ]

	encoder = MultiLabelBinarizer()
	train_targets = encoder.fit_transform(train_categories)
	test_targets = encoder.fit_transform(test_categories)
	target_names = encoder.classes_
	
	assert len(target_names) == len(categories)
	
	print("len(train_docs):",len(train_docs))
	print("len(test_docs):",len(test_docs))

	print("class balance for train:", 100*sum(train_targets)/len(train_targets))
	print("class balance for test:", 100*sum(test_targets)/len(test_targets))

	sys.stdout.flush()

	clf = DocumentClassifier(params)

	print('train_targets.shape=',train_targets.shape)
	sys.stdout.flush()

	clf.fit(train_docs, train_targets, target_names)

	predictions = clf.predict(test_docs)

	print('predictions.shape=',predictions.shape)
	sys.stdout.flush()

	results = {}

	all_tn, all_fp, all_fn, all_tp = 0,0,0,0

	all_precisions, all_recalls, all_f1_scores = [],[],[]

	for i,label in enumerate(target_names):
		gold_for_label = test_targets[:,i]
		predictions_for_label = predictions[:,i] > 0.5
		
		tn, fp, fn, tp = sklearn.metrics.confusion_matrix(gold_for_label, predictions_for_label).ravel()
		tn, fp, fn, tp = map(int, [tn, fp, fn, tp])

		all_tn += tn
		all_fp += fp
		all_fn += fn
		all_tp += tp

		precision = sklearn.metrics.precision_score(gold_for_label,predictions_for_label)
		recall = sklearn.metrics.recall_score(gold_for_label,predictions_for_label)
		f1_score = sklearn.metrics.f1_score(gold_for_label,predictions_for_label)

		all_precisions.append(precision)
		all_recalls.append(recall)
		all_f1_scores.append(f1_score)

		print(f"{label}\t{precision}\t{recall}\t{f1_score}")
		sys.stdout.flush()
		results[label] = {'tn':tn,'fp':fp,'fn':fn,'tp':tp,'precision':precision,'recall':recall,'f1_score':f1_score}

	micro_precision = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 0
	micro_recall = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 0
	micro_f1 = 2 * (micro_precision * micro_recall) / (micro_precision + micro_recall) if (micro_precision + micro_recall) > 0 else 0

	macro_precision = sum(all_precisions) / len(all_precisions)
	macro_recall = sum(all_recalls) / len(all_recalls)
	macro_f1 = sum(all_f1_scores) / len(all_f1_scores)

	results['MICRO'] = {'tn':all_tn,'fp':all_fp,'fn':all_fn,'tp':all_tp,'precision':micro_precision,'recall':micro_recall,'f1_score':micro_f1}
	results['MACRO'] = {'precision':macro_precision,'recall':macro_recall,'f1_score':macro_f1}

	print("-"*30)
	print(f"MICRO\t{micro_precision}\t{micro_recall}\t{micro_f1}")
	print(f"MACRO\t{macro_precision}\t{macro_recall}\t{macro_f1}")
	print("-"*30)

	output = {'params':params, 'results':results}

	print(json.dumps(output))

	print("Done")

if __name__ == '__main__':
	main()
	
