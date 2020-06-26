import argparse
import pickle
import json
from collections import defaultdict

from utils import DocumentVectorizer
from sklearn.linear_model import LogisticRegression

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Annotate documents with publication type (e.g. research article, review, news, etc)')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
	
	print("Loading documents...")
	
	with open(args.inJSON) as f:
		documents = json.load(f)
	
	annotated = [ d for d in documents if len(d['annotations']) > 0]
	annotated = [ d for d in annotated if not any(a in d['annotations'] for a in ['Skip','Maybe'])]
	unannotated = [ d for d in documents if len(d['annotations']) == 0]
	
	selected_annotations = ['Review','Updates','Comment/Editorial','Meta-analysis','News','NotRelevant','Research']
	for d in annotated:
		annotated_pubtypes = [ a for a in selected_annotations if a in d['annotations'] ]
		if 'NotRelevant' in annotated_pubtypes:
			annotated_pubtypes = ['NotRelevant']
			
		assert len(annotated_pubtypes) <= 1, "Document has %s" % (str(annotated_pubtypes))
		if len(annotated_pubtypes) == 0:
			annotated_pubtypes = ['Research']
			
		d['annotated_pubtype'] = annotated_pubtypes[0]
		
	print("Vectorizing...")
	documentVectorizer = DocumentVectorizer()
	X = documentVectorizer.fit_transform(annotated)
	X_all = documentVectorizer.transform(documents)
	y = [ d['annotated_pubtype'] for d in annotated ]
	
	print("Training...")
	clf = LogisticRegression(class_weight='balanced',random_state=0)
	clf.fit(X,y)

	print("Predicting...")
	predicted = clf.predict(X_all)
	
	for p,d in zip(predicted,documents):
		assert len(annotated_pubtypes) <= 1, "Document has %s" % (str(annotated_pubtypes))
		
		if 'annotated_pubtype' in d:
			d['ml_pubtype'] = d['annotated_pubtype']
			del d['annotated_pubtype']
		else:
			d['ml_pubtype'] = p
			
			
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)