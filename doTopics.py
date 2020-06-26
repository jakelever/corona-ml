import argparse
import json
import re
from collections import Counter

from utils import DocumentVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multiclass import OneVsRestClassifier

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Annotate the topics of the documents')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
	
	print("Loading documents...")
	with open(args.inJSON) as f:
		documents = json.load(f)
	
	print("Preprocessing topic annotations...")	
	
	annotated = [ d for d in documents if len(d['annotations']) > 0 ]
    
	filters = {'RemoveFromCorpus?','NotAllEnglish','NotRelevant','Skip','Maybe'}
	filters.update({'Review','Updates','Comment/Editorial','News','Meta-analysis'})
	#filters.update({'Updates','Comment/Editorial','News','Meta-analysis','Guidelines'})
	#filters.update({'News'})

	annotated = [ d for d in annotated if not any (f in d['annotations'] for f in filters) ]

	toRemove = ['SARS-CoV','MERS-CoV','SARS-CoV-2','None','NotMainFocus']
	toRemove.append('Clinical Trial')
	#toRemove.append('Review','Comment/Editorial','Meta-analysis','News','NotRelevant')
	
	groupings = {}
	groupings['Drug Repurposing'] = 'Therapeutics'
	groupings['Novel therapeutics'] = 'Therapeutics'
	groupings['Host Biology'] = 'Molecular Biology'
	groupings['Viral Biology'] = 'Molecular Biology'
	groupings['Case Report / Series'] = 'Patient Reports'
	groupings['Observational Study'] = 'Patient Reports'
	groupings['Forecasting/Modelling'] = 'Disease Modelling'
	
	for g in groupings:
		assert any( a == g for d in documents for a in d['annotations']), "Couldn't find any annotations for %s" % g
	
	for d in documents:
		d['annotated_topics'] = d['annotations']
		d['annotated_topics'] = [ a for a in d['annotated_topics'] if not a in toRemove ]
		d['annotated_topics'] = [ (groupings[a] if a in groupings else a) for a in d['annotated_topics'] ]
		d['annotated_topics'] = sorted(set(d['annotated_topics']))
		
	print("Vectorizing...")
	documentVectorizer = DocumentVectorizer()
	X = documentVectorizer.fit_transform(annotated)
	X_all = documentVectorizer.transform(documents)
	
	
	encoder = MultiLabelBinarizer()
	y = encoder.fit_transform( [ d['annotated_topics'] for d in annotated ] )
	
	#label_to_column = { l:i for i,l in enumerate(encoder.classes_) }
	#print(encoder.classes_)
	print(Counter( sorted([ a for d in annotated for a in d['annotated_topics'] ]) ))
	
	print("Training...")
	clf = OneVsRestClassifier(LogisticRegression(class_weight='balanced',random_state=0))
	clf.fit(X,y)
	
	predictions = clf.predict(X_all)
	
	for d in documents:
		if not 'topics' in d:
			d['topics'] = []
	
	topicCounter = Counter()
	for doc_index,label_index in zip(*predictions.nonzero()):
		d = documents[doc_index]
		#print(doc_index,label_index)
			
		if len(d['annotated_topics']) > 0:
			d['topics'] += d['annotated_topics']
		else:
			topic = encoder.classes_[label_index]
			d['topics'].append(topic)
			topicCounter[topic] += 1
			
	# Cleanup and note the documents that were excluded
	for d in documents:
		d['exclude'] = any (f in d['annotations'] for f in filters)
		del d['annotated_topics']
						
	print(topicCounter)
		
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)