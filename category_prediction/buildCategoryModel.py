
import sys
import argparse
import json
import os
from sklearn.preprocessing import MultiLabelBinarizer

from coronacode import DocumentClassifier


def main():
	parser = argparse.ArgumentParser('Build a model for a classifier')
	parser.add_argument('--categoriesFile',required=True,type=str,help='Category list file')
	parser.add_argument('--params',required=True,type=str,help='JSON string with parameters')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--outModelDir',required=True,type=str,help='Output directory to store model data')
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

	train_docs = [ d for d in documents if len(d['annotations']) > 0 ]
	#other_docs = [ d for d in documents if len(d['annotations']) == 0 ]

	toRemoveFromTraining = {'RemoveFromCorpus?','NotAllEnglish','NotRelevant','Skip','Maybe','FixAbstract'}
	train_docs = [ d for d in train_docs if not any (f in d['annotations'] for f in toRemoveFromTraining) ]

	train_categories = [ [ a for a in d['annotations'] if a in categories ] for d in train_docs ]

	encoder = MultiLabelBinarizer()
	train_targets = encoder.fit_transform(train_categories)
	target_names = encoder.classes_.tolist()

	assert len(target_names) == len(categories)
	
	print("len(train_docs):",len(train_docs))

	print("class balance for train:", 100*sum(train_targets)/len(train_targets))
	sys.stdout.flush()

	clf = DocumentClassifier(params)

	clf.fit(train_docs, train_targets, target_names)

	clf.save(args.outModelDir)

	print("Saving to %s" % args.outModelDir)
	categories_file = os.path.join(args.outModelDir,'categories.json')
	with open(categories_file,'w') as f:
		json.dump(target_names,f)

	print("Done")

if __name__ == '__main__':
	main()
	
