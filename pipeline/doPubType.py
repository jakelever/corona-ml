import argparse
import pickle
import json
from collections import defaultdict,Counter

from utils import DocumentVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import Pipeline

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
	
	selected_annotations = ['Review','Updates','Comment/Editorial','Meta-analysis','News','NotRelevant','Research','Book chapter']
	for d in annotated:
		annotated_pubtypes = [ a for a in selected_annotations if a in d['annotations'] ]
		if 'NotRelevant' in annotated_pubtypes:
			annotated_pubtypes = ['NotRelevant']
			
		assert len(annotated_pubtypes) <= 1, "Document has %s" % (str(annotated_pubtypes))
		if len(annotated_pubtypes) == 0:
			annotated_pubtypes = ['Research']
			
		d['annotated_pubtype'] = annotated_pubtypes[0]
		
	print("Removing book chapters from training - will get with simple title check")
	annotated = [ d for d in annotated if not d['annotated_pubtype'] == 'Book chapter' ]
		
	print("Vectorizing...")
	#documentVectorizer = DocumentVectorizer()
	#X = documentVectorizer.fit_transform(annotated)
	#X_all = documentVectorizer.transform(documents)
	y = [ d['annotated_pubtype'] for d in annotated ]
	
	pipeline = Pipeline([
		("vectorizer", DocumentVectorizer(features=['titleabstract'])),
		("classifier", LogisticRegression(class_weight='balanced',random_state=0))
	])
	
	print("Training...")
	#clf = LogisticRegression(class_weight='balanced',random_state=0)
	#clf.fit(X,y)
	pipeline.fit(annotated,y)
	
	probs = pipeline.predict_proba(documents)
	
	class_to_column = { c:i for i,c in enumerate(pipeline.classes_) }

	#print("Predicting...")
	#predicted = clf.predict(X_all)
	print("Classes:", pipeline.classes_)
	
	updates_journals = set(['MMWR. Morbidity and mortality weekly report','MMWR Morb Mortal Wkly Rep'])
	
	#for p,d in zip(predicted,documents):
	for i,d in enumerate(documents):
		mesh_pubtypes = d['pub_type'] if 'pub_type' in d else []
		if 'Review' in mesh_pubtypes: # If it's tagged as a Review, it's definitely not research or news, but could be more than Review
			probs[i,class_to_column['Research']] = -1
			probs[i,class_to_column['News']] = -1
		
		max_index = probs[i,:].argmax()
		score = probs[i,max_index]
		if score > 0.6:
			predicted_pubtype = pipeline.classes_[max_index]
		else:
			predicted_pubtype = 'Research'
			
		if d['journal'] in updates_journals:
			predicted_pubtype = 'Updates'
		
		assert len(annotated_pubtypes) <= 1, "Document has %s" % (str(annotated_pubtypes))
		
		if 'annotated_pubtype' in d:
			d['ml_pubtype'] = d['annotated_pubtype']
			del d['annotated_pubtype']
		elif any('Clinical Trial' in pt for pt in mesh_pubtypes):
			d['ml_pubtype'] = 'Research'
		elif any (pt in mesh_pubtypes for pt in ['News','Newspaper Article'] ):
			d['ml_pubtype'] = 'News'
		elif any (pt in mesh_pubtypes for pt in ['Systematic Review','Meta-Analysis'] ):
			d['ml_pubtype'] = 'Meta-analysis'
		elif any (pt in mesh_pubtypes for pt in ['Editorial','Comment'] ):
			d['ml_pubtype'] = 'Comment/Editorial'
		elif 'Published Erratum' in mesh_pubtypes or d['title'].lower().startswith('erratum'):
			d['ml_pubtype'] = 'Erratum'
		elif d['title'].startswith('Chapter '):
			d['ml_pubtype'] = 'Book chapter'
		else:
			d['ml_pubtype'] = predicted_pubtype
			
			
	print(Counter( d['ml_pubtype'] for d in documents))
			
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)