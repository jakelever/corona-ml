import argparse
import json
import re
from collections import Counter

from utils import DocumentVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import Pipeline

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Annotate the topics of the documents')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
	
	print("Loading documents...")
	with open(args.inJSON) as f:
		documents = json.load(f)
	
	print("Preprocessing topic annotations...")	
	
	groupings = {}
	groupings['Host Biology'] = 'Molecular Biology'
	groupings['Viral Biology'] = 'Molecular Biology'
	groupings['Drug Targets'] = 'Molecular Biology'
	groupings['Drug Repurposing'] = 'Therapeutics'
	groupings['Novel Therapeutics'] = 'Therapeutics'
	
	allowedTopics = {'Diagnostics', 'Disease Spread', 'Forecasting & Modelling', 'Healthcare Workers', 'Imaging', 'Immunology', 'Medical Devices', 'Model Systems & Tools', 'Molecular Biology', 'Non-human', 'Pediatrics', 'Prevalence', 'Prevention', 'Psychology', 'Risk Factors', 'Surveillance', 'Symptoms', 'Therapeutics', 'Transmission', 'Vaccines'}
	
	for g in groupings:
		assert any( a == g for d in documents for a in d['annotations']), "Couldn't find any annotations for %s" % g
		
	for d in documents:
		d['annotated_topics'] = d['annotations']
		d['annotated_topics'] = [ (groupings[a] if a in groupings else a) for a in d['annotated_topics'] ]
		d['annotated_topics'] = [ a for a in d['annotated_topics'] if a in allowedTopics ]
		d['annotated_topics'] = sorted(set(d['annotated_topics']))
		
	for t in allowedTopics:
		assert any( a == t for d in documents for a in d['annotated_topics']), "Couldn't find any annotations for %s" % t
	
		
	annotated = [ d for d in documents if len(d['annotated_topics']) > 0 ]
	
	toRemoveFromTraining = {'RemoveFromCorpus?','NotAllEnglish','NotRelevant','Skip','Maybe','FixAbstract'}
	annotated = [ d for d in annotated if not any (f in d['annotations'] for f in toRemoveFromTraining) ]
		
	#print(Counter( at for d in annotated for at in d['annotated_topics'] ))
	#assert False
		
	#print("Vectorizing...")
	#documentVectorizer = DocumentVectorizer()
	#X = documentVectorizer.fit_transform(annotated)
	#X_all = documentVectorizer.transform(documents)
	
	
	encoder = MultiLabelBinarizer()
	y = encoder.fit_transform( [ d['annotated_topics'] for d in annotated ] )
	
	pipeline = Pipeline([
		("vectorizer", DocumentVectorizer(features=['titleabstract'])),
		("dimreducer", TruncatedSVD(n_components=64,random_state=0)),
		("classifier", OneVsRestClassifier(LogisticRegression(class_weight='balanced',random_state=0,C=21)))
	])
	
	#label_to_column = { l:i for i,l in enumerate(encoder.classes_) }
	#print(encoder.classes_)
	#print(Counter( sorted([ a for d in annotated for a in d['annotated_topics'] ]) ))
	
	#print("Training...")
	#clf = OneVsRestClassifier(LogisticRegression(class_weight='balanced',random_state=0))
	pipeline.fit(annotated,y)
	
	probs = pipeline.predict_proba(documents)
	
	print("Selecting high confidence predictions")
	probs_mask = (probs > 0.75)	
	probs = probs * probs_mask
	
	for d in documents:
		if not 'topics' in d:
			d['topics'] = []
	
	for doc_index,label_index in zip(*probs.nonzero()):
		d = documents[doc_index]
		#print(doc_index,label_index)
			
		if len(d['annotated_topics']) > 0:
			d['topics'] += d['annotated_topics']
		else:
			topic = encoder.classes_[label_index]
			d['topics'].append(topic)
			
			
	title_keywords = ['misinformation','cord19','cord-19','cord 19','conspiracy','journalism']
	journal_keywords = ['economic','political','water','economische','journalism','legal','finance','financ.','financial']
	journal_regexes = [ re.compile(r'\b%s\b' % k,flags=re.IGNORECASE) for k in ['econ','law'] ]
	nonmedical_journals = {'joule'}
	# Rule-based for non-medical
	for d in documents:
		is_nonmedical = False
		if any( k in d['title'].lower() for k in title_keywords ):
			is_nonmedical = True
		elif any( k in d['journal'].lower() for k in journal_keywords ):
			is_nonmedical = True
		elif any( regex.search(d['journal']) for regex in journal_regexes ):
			is_nonmedical = True
		elif d['journal'].lower() in nonmedical_journals:
			is_nonmedical = True
		elif 'Non-medical' in d['annotations']:
			is_nonmedical = True
			
		if is_nonmedical:
			d['topics'] = ['Non-medical']
						
	# Cleanup and note the documents that were excluded
	for d in documents:
		d['topics'] = sorted(set(d['topics']))
		d['exclude'] = any (f in d['annotations'] for f in toRemoveFromTraining)
		del d['annotated_topics']
						
						
	topicCounter = Counter( t for d in documents for t in d['topics'] )
	print(topicCounter)
		
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)