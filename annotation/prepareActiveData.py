import sys
sys.path.append("../pipeline")

from utils import associated_annotations_with_documents

import mysql.connector
import json
import argparse
import pickle
import numpy as np
import os

from collections import Counter
from utils import DocumentVectorizer

from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.decomposition import TruncatedSVD

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Prepare data for active learning')
	parser.add_argument('--db',required=True,type=str,help='JSON with database settings')
	parser.add_argument('--inDocs',required=True,type=str,help='Input file with all the documents')
	parser.add_argument('--inAltmetric',required=True,type=str,help='Input file with the Altmetric data')
	parser.add_argument('--negThreshold',required=False,default=0.3,type=float,help='Threshold below which is a confident negative (default=0.25)')
	parser.add_argument('--posThreshold',required=False,default=0.7,type=float,help='Threshold above which is a confident positive (default=0.75)')
	parser.add_argument('--outDir',required=True,type=str,help='Output dir to put matrices')
	#parser.add_argument('--outFile',required=True,type=str,help='Output file to put matrices and stuff')
	args = parser.parse_args()
	
	with open(args.db) as f:
		database = json.load(f)

	mydb = mysql.connector.connect(
		host=database['host'],
		user=database['user'],
		passwd=database['passwd'],
		database=database['database']
	)
	mycursor = mydb.cursor()
	
	with open(args.inDocs) as f:
		documents = json.load(f)
	print("len(documents)=", len(documents))
	
	for d in documents:
		d['annotations'] = []
	associated_annotations_with_documents(documents,mydb)
	
	with open(args.inAltmetric) as f:
		altmetric_data = json.load(f)
	altmetric_data = { (ad['identifiers']['cord_uid'],ad['identifiers']['pubmed_id'],ad['identifiers']['doi']) : ad for ad in altmetric_data }
	print("len(altmetric_data)=",len(altmetric_data))
	
	for d in documents:
		altmetric_id = (d['cord_uid'],d['pubmed_id'],d['doi'])
		if altmetric_id in altmetric_data:
			d['altmetric'] = altmetric_data[altmetric_id]
		
	altmetric_docs = [ d for d in documents if 'altmetric' in d]
	print("len(altmetric_data)=",len(altmetric_docs))
	
	annotated = [ d for d in documents if d['annotations']]

	toFilter = {'Maybe','Skip'}
	annotated = [ d for d in annotated if not any (a in d['annotations'] for a in toFilter)]
	print("len(annotated)=",len(annotated))

	#toRemove = {'SARS-CoV','SARS-CoV-2','MERS-CoV','None'}

	mapping = {}
	mapping['Observational Study'] = 'Case Reports'
	mapping['Case Report / Series'] = 'Case Reports'
	mapping['Diagnostics'] = 'Diagnostics'
	mapping['Prevalence'] = 'Prevalence'
	mapping['Viral Biology'] = 'Molecular Biology'
	mapping['Host Biology'] = 'Molecular Biology'
	mapping['Transmission'] = 'Transmission'
	mapping['Non-therapeutic interventions'] = 'Non-therapeutic interventions'
	mapping['Drug Repurposing'] = 'Therapeutics'
	mapping['Novel therapeutics'] = 'Therapeutics'
	#mapping['Clinical Trial'] = 'Clinical Trial'
	mapping['Immunology'] = 'Immunology'
	mapping['Psychology'] = 'Psychology'
	mapping['Vaccines'] = 'Vaccines'
	mapping['Forecasting/Modelling'] = 'Disease Modelling'
	for d in annotated:
		#d['annotations'] = [ a for a in d['annotations'] if not a in toRemove ]
		
		d['annotated_topics'] = [ mapping[a] for a in d['annotations'] if a in mapping ]
			
		if 'Review' in d['annotations']:
			d['annotated_topics'] = ['Review']
		
		if len(d['annotated_topics']) == 0:
			d['annotated_topics'] = ['Other']

	#Counter( sorted(a for d in annotated for a in d['annotations']) )
	Counter( a for d in annotated for a in d['annotated_topics'] )
	
	challenge_docs = [ d for d in altmetric_docs if d['altmetric']['score'] > 100 and not d in annotated ]
	print("len(challenge_docs)=",len(challenge_docs))
	

	encoder = MultiLabelBinarizer()
	y_annotated = encoder.fit_transform( [ d['annotated_topics'] for d in annotated ] )

	pipeline = Pipeline([
		("vectorizer", DocumentVectorizer(features=['titleabstract'])),
		("dimreducer", TruncatedSVD(n_components=64,random_state=0)),
		("classifier", OneVsRestClassifier(LogisticRegression(class_weight='balanced',random_state=0,C=21)))
	])

	pipeline.fit(annotated, y_annotated)

	scores = pipeline.predict_proba(challenge_docs)
	print("scores.shape=",scores.shape)
	print("len(encoder.classes_)=",len(encoder.classes_))
	
	numHasHighConfidence = int(sum(scores.max(axis=1) > args.posThreshold))
	numHasOnlyLowConfidence = int(sum(scores.max(axis=1) < args.negThreshold))
	
	percHasHighConfidence = 100*numHasHighConfidence/scores.shape[0]

	print("numHasHighConfidence = %d" % numHasHighConfidence)
	print("percHasHighConfidence = %.1f%%" % percHasHighConfidence)
	print("numHasOnlyLowConfidence = %d" % numHasOnlyLowConfidence)
	
	confidence_records = []
	for label_index,label in enumerate(encoder.classes_):
		numHighConfPositive = int(sum(scores[:,label_index] > args.posThreshold))
		numHighConfNegative = int(sum(scores[:,label_index] < args.negThreshold))
		
		percHighConfPositive = 100*numHighConfPositive/scores.shape[0]
		percHighConfNegative = 100*numHighConfNegative/scores.shape[0]
		
		confidence_record = [label_index,label,numHighConfPositive,numHighConfNegative,percHighConfPositive,percHighConfNegative]
		confidence_records.append(confidence_record)
		
		print("%d\t%s\t%.1f\t%.1f\t%.1f" % (label_index,label,percHighConfPositive,percHighConfNegative,percHighConfPositive+percHighConfNegative))
		
	delete_sql = "DELETE FROM confidencescores"
	print(delete_sql)
	mycursor.execute(delete_sql)
	
	insert_sql = "INSERT INTO confidencescores(confidence_id,name,num_high,num_low,perc_high,perc_low) VALUES(%s,%s,%s,%s,%s,%s)"
	print(insert_sql)
	
	mycursor.executemany(insert_sql, confidence_records)
	mydb.commit()
	
	undecided_indices = [ i for i,max_score in enumerate(scores.max(axis=1)) if max_score < args.posThreshold ]
	undecided_docs = [ challenge_docs[i] for i in undecided_indices ]
	undecided_scores = scores[undecided_indices,:]
	
	print("len(undecided_docs)=",len(undecided_docs))
	
	pipeline = Pipeline([
				("vectorizer", DocumentVectorizer(features=['titleabstract'])),
				("dimreducer", TruncatedSVD(n_components=64,random_state=0))
	])

	X_annotated = pipeline.fit_transform(annotated)
	X_undecided = pipeline.transform(undecided_docs)

	print("X_annotated.shape=",X_annotated.shape)
	print("X_undecided.shape=",X_undecided.shape)
	print("y_annotated.shape=",y_annotated.shape)
	
	np.save(os.path.join(args.outDir,'X_annotated.npy'), X_annotated)
	np.save(os.path.join(args.outDir,'X_undecided.npy'), X_undecided)
	np.save(os.path.join(args.outDir,'y_annotated.npy'), y_annotated)
	np.save(os.path.join(args.outDir,'undecided_scores.npy'), undecided_scores)
	
	with open(os.path.join(args.outDir,'undecided_docs.pickle'),'wb') as f:
		pickle.dump(undecided_docs, f)
	
	print("Saved.")