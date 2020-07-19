import sys
sys.path.append("../pipeline")

from utils import associated_annotations_with_documents

import ray
import mysql.connector
import json
import argparse
import pickle
import numpy as np
import os
import sys
import random
import time

from collections import Counter
from utils import DocumentVectorizer

from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.decomposition import TruncatedSVD

def is_activequeue_empty(mydb,task_id):
	mycursor = mydb.cursor()
	
	sql = "SELECT document_id FROM activequeue WHERE task_id = %d AND document_id NOT IN (SELECT document_id FROM annotations WHERE task_id = %d) LIMIT 1" % (task_id,task_id)
	#print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()

	return len(myresult) == 0

def load_document_id_mapping(mydb,documents):
	mycursor = mydb.cursor()
	
	sql = "SELECT document_id,pubmed_id,cord_uid FROM documents"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()

	pubmed_to_document_id = {}
	cord_to_document_id = {}

	pubmed_to_document_id = {str(pubmed_id):document_id for document_id,pubmed_id,cord_ui in myresult if pubmed_id }
	cord_to_document_id = {cord_ui:document_id for document_id,pubmed_id,cord_ui in myresult if cord_ui }
	
	for d in documents:
		cord_uid = d['cord_uid']
		pubmed_id = d['pubmed_id']

		if cord_uid in cord_to_document_id:
			document_id = cord_to_document_id[cord_uid]
		elif pubmed_id in pubmed_to_document_id:
			document_id = pubmed_to_document_id[pubmed_id]
		else:
			continue
			#raise RuntimeError("Couldn't find matching document for annotation with cord_uid=%s and pubmed_id=%s" % (cord_uid,pubmed_id))
			
		d['document_id'] = document_id

def remap_annotations(annotated):
	toRemoveFromTraining = {'RemoveFromCorpus?','NotAllEnglish','NotRelevant','Skip','Maybe','FixAbstract'}
	#toRemoveFromTraining.update({'Review','Updates','Comment/Editorial','News','Meta-analysis'})
	#toRemoveFromTraining.update({'Updates','Comment/Editorial','News','Meta-analysis','Guidelines'})
	#toRemoveFromTraining.update({'News'})

	annotated = [ d for d in annotated if not any (f in d['annotations'] for f in toRemoveFromTraining) ]

	annotationsToStrip = ['SARS-CoV','MERS-CoV','SARS-CoV-2','None','NotMainFocus']
	annotationsToStrip.append('Clinical Trial')
	annotationsToStrip.extend(['Review','Comment/Editorial','Meta-analysis','News','NotRelevant','Updates','Book chapter'])
	
	groupings = {}
	groupings['Host Biology'] = 'Molecular Biology'
	groupings['Viral Biology'] = 'Molecular Biology'
	groupings['Drug Repurposing'] = 'Therapeutics'
	groupings['Novel Therapeutics'] = 'Therapeutics'
	
	for g in groupings:
		assert any( a == g for d in documents for a in d['annotations']), "Couldn't find any annotations for %s" % g
	
	for d in documents:
		d['annotated_topics'] = d['annotations']
		d['annotated_topics'] = [ a for a in d['annotated_topics'] if not a in annotationsToStrip ]
		d['annotated_topics'] = [ (groupings[a] if a in groupings else a) for a in d['annotated_topics'] ]
		d['annotated_topics'] = sorted(set(d['annotated_topics']))
		
	return annotated

def connect_db(dbfile):
	with open(dbfile) as f:
		database = json.load(f)

	mydb = mysql.connector.connect(
		host=database['host'],
		user=database['user'],
		passwd=database['passwd'],
		database=database['database'],
		autocommit=True
	)
	return mydb
	
def associate_altmetric_data_with_documents(documents, altmetric_filename):
	with open(altmetric_filename) as f:
		altmetric_data = json.load(f)
	altmetric_data = { (ad['identifiers']['cord_uid'],ad['identifiers']['pubmed_id'],ad['identifiers']['doi']) : ad for ad in altmetric_data }
	
	for d in documents:
		altmetric_id = (d['cord_uid'],d['pubmed_id'],d['doi'])
		if altmetric_id in altmetric_data:
			d['altmetric'] = altmetric_data[altmetric_id]
			
def insert_document_into_db(mydb,doc):
	mycursor = mydb.cursor()
	
	columns = [ 'pubmed_id', 'cord_uid', 'title', 'abstract', 'publish_year', 'journal', 'url' ]
	
	if doc['pubmed_id']:
		doc['url'] = "https://pubmed.ncbi.nlm.nih.gov/%s" % doc['pubmed_id']
	elif doc['doi']:
		doc['url'] = "https://doi.org/%s" % doc['doi']
	else:
		urls = [ u.strip() for u in doc['url'].split(';') ]
		doc['url'] = urls[0]
	
	phase = 'activelearning'
	record = [ doc[c] for c in columns ] + [ phase ]
	
	insertsql = "INSERT INTO documents (%s,phase,added) VALUES (%s,%%s,NOW())" % (",".join(columns),",".join([ '%s' for _ in columns ]))
	
	mycursor.execute(insertsql, record)
	#mydb.commit()
	
	doc['document_id'] = mycursor.lastrowid
	
def add_doc_to_queue(mydb,doc,task_id,dochash,current_coverage):
	mycursor = mydb.cursor()
	
	insertsql = "INSERT INTO activequeue (document_id,task_id,dochash,current_coverage,added) VALUES(%s,%s,%s,%s,NOW()) "
	
	record = [ doc['document_id'], task_id, dochash, current_coverage ]
	
	mycursor.execute(insertsql, record)
	#mydb.commit()

def get_y_and_undecided_docs(annotated,challenge_docs,posThreshold,negThreshold):
	encoder = MultiLabelBinarizer()
	y_annotated = encoder.fit_transform( [ d['annotated_topics'] for d in annotated ] )

	pipeline = Pipeline([
		("vectorizer", DocumentVectorizer(features=['titleabstract'])),
		("dimreducer", TruncatedSVD(n_components=64,random_state=0)),
		("classifier", OneVsRestClassifier(LogisticRegression(class_weight='balanced',random_state=0,C=21)))
	])

	pipeline.fit(annotated, y_annotated)

	scores = pipeline.predict_proba(challenge_docs)
	
	numHasHighConfidence = int(sum(scores.max(axis=1) > posThreshold))
	numHasOnlyLowConfidence = int(sum(scores.max(axis=1) < negThreshold))
	percHasHighConfidence = 100*numHasHighConfidence/scores.shape[0]
	
	confidence_records = []
	for label_index,label in enumerate(encoder.classes_):
		numHighConfPositive = int(sum(scores[:,label_index] > posThreshold))
		numHighConfNegative = int(sum(scores[:,label_index] < negThreshold))
		
		percHighConfPositive = 100*numHighConfPositive/scores.shape[0]
		percHighConfNegative = 100*numHighConfNegative/scores.shape[0]
		
		confidence_record = [label_index,label,numHighConfPositive,numHighConfNegative,percHighConfPositive,percHighConfNegative]
		confidence_records.append(confidence_record)
		
		print("%d\t%s\t%.1f\t%.1f\t%.1f" % (label_index,label,percHighConfPositive,percHighConfNegative,percHighConfPositive+percHighConfNegative))
		
	#delete_sql = "DELETE FROM confidencescores"
	#print(delete_sql)
	#mycursor.execute(delete_sql)
	
	#insert_sql = "INSERT INTO confidencescores(confidence_id,name,num_high,num_low,perc_high,perc_low) VALUES(%s,%s,%s,%s,%s,%s)"
	#print(insert_sql)
	
	#mycursor.executemany(insert_sql, confidence_records)
	#mydb.commit()
	
	undecided_indices = [ i for i,max_score in enumerate(scores.max(axis=1)) if max_score < posThreshold ]
	undecided_docs = [ challenge_docs[i] for i in undecided_indices ]
	undecided_scores = scores[undecided_indices,:]
	
	return y_annotated, undecided_docs
	
def vectorizer_docs(annotated, undecided_docs):
	pipeline = Pipeline([
				("vectorizer", DocumentVectorizer(features=['titleabstract'])),
				("dimreducer", TruncatedSVD(n_components=64,random_state=0))
	])

	X_annotated = pipeline.fit_transform(annotated)
	X_undecided = pipeline.transform(undecided_docs)
	
	return X_annotated, X_undecided
	
def get_multiscores(X_train,y_train,X_test):
	assert y_train.shape[1] > 1
	
	clf = OneVsRestClassifier(LogisticRegression(class_weight='balanced',random_state=0,C=21))

	clf.fit(X_train, y_train)
	
	scores = clf.predict_proba(X_test)
	
	return scores
	
def get_scores(X_train,y_train,X_test):
	clf = LogisticRegression(class_weight='balanced',random_state=0,C=21)

	clf.fit(X_train, y_train)
	
	assert clf.classes_.tolist() == [0,1]
	
	scores = clf.predict_proba(X_test)[:,1]
	
	return scores
	
@ray.remote
def evaluate_document_choice(docindex,X_annotated,y_annotated,X_undecided,posThreshold):
	outcomes = []
	
	X_annotated_plus_one = np.vstack([X_annotated,np.zeros((1,X_annotated.shape[1]))])
	X_annotated_plus_one[X_annotated_plus_one.shape[0]-1,:] = X_undecided[docindex,:]
			
	#neg_matrix = np.zeros((X_undecided.shape[0],y_annotated.shape[1]))
	#for label_index in range(y_annotated.shape[1]):
	#	y_with_artifical_addition = np.concatenate([y_annotated[:,label_index],[0]])
	#	neg_scores = get_scores(X_annotated_plus_one, y_with_artifical_addition, X_undecided)
	#	neg_matrix[:,label_index] = neg_scores
		
	y_with_artifical_addition = np.vstack([y_annotated,np.zeros((1,y_annotated.shape[1]))])
	neg_matrix = get_multiscores(X_annotated_plus_one,y_with_artifical_addition,X_undecided)
	
	for label_index in range(y_annotated.shape[1]):
		y_with_artifical_addition = np.concatenate([y_annotated[:,label_index],[1]])
		pos_scores = get_scores(X_annotated_plus_one, y_with_artifical_addition, X_undecided)
		
		pos_matrix = neg_matrix.copy()
		pos_matrix[:,label_index] = pos_scores
		
		num_has_high_conf_positive = int(sum(pos_matrix.max(axis=1) > posThreshold))
		outcomes.append(num_has_high_conf_positive)
		
	return outcomes
	
def calculate_outcomes_of_different_document_choices_old(X_annotated,y_annotated,X_undecided,posThreshold):
	outcomes = [ evaluate_document_choice.remote(docindex,X_annotated,y_annotated,X_undecided,posThreshold) for docindex in range(X_undecided.shape[0]) ]
			
	outcomes = ray.get(outcomes)
	
	outcomes = np.array(outcomes)
	
	assert outcomes.shape == (X_undecided.shape[0],y_annotated.shape[1]), "Got %s, expected %s" % (str(outcomes.shape),str((X_undecided.shape[0],y_annotated.shape[1])))
			
	return outcomes
	
def calculate_outcomes_of_different_document_choices(X_annotated,y_annotated,X_undecided,posThreshold,num_docs=200):
	doc_indices = random.sample(range(X_undecided.shape[0]),min(num_docs,X_undecided.shape[0]))

	some_outcomes = [ evaluate_document_choice.remote(docindex,X_annotated,y_annotated,X_undecided,posThreshold) for docindex in doc_indices ]
	some_outcomes = ray.get(some_outcomes)
	
	outcomes = np.full((X_undecided.shape[0],y_annotated.shape[1]), -1)
	for docindex,some_outcome in zip(doc_indices,some_outcomes):
		outcomes[docindex,:] = some_outcome
	
	assert outcomes.shape == (X_undecided.shape[0],y_annotated.shape[1]), "Got %s, expected %s" % (str(outcomes.shape),str((X_undecided.shape[0],y_annotated.shape[1])))
			
	return outcomes

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Prepare data for active learning')
	parser.add_argument('--db',required=True,type=str,help='JSON with database settings')
	parser.add_argument('--inDocs',required=True,type=str,help='Input file with all the documents')
	parser.add_argument('--inAltmetric',required=True,type=str,help='Input file with the Altmetric data')
	parser.add_argument('--mode',required=False,default="bestoutcome",type=str,help='Mode to select next document (bestoutcome/popular)')
	parser.add_argument('--altmetricThreshold',required=False,type=int,default=100,help='Altmetric score to threshold to identify docs for annotation')
	parser.add_argument('--negThreshold',required=False,default=0.3,type=float,help='Threshold below which is a confident negative (default=0.25)')
	parser.add_argument('--posThreshold',required=False,default=0.7,type=float,help='Threshold above which is a confident positive (default=0.75)')
	args = parser.parse_args()
	
	assert args.mode in ['bestoutcome','popular']
	
	task_id = 2
	
	#ray.init(address='auto', redis_password='5241590000000000')
	ray.init()
	
	mydb = connect_db(args.db)
	
	print("Loading all documents with database IDs and getting Altmetric data...")
	with open(args.inDocs) as f:
		documents = json.load(f)
	load_document_id_mapping(mydb, documents)
	associate_altmetric_data_with_documents(documents,args.inAltmetric)
	
	while True:
		
		print("Waiting for empty queue...")
		while not is_activequeue_empty(mydb,task_id):
			time.sleep(1)
	
		print("Loading annotations...")
		for d in documents:
			d['annotations'] = []
		associated_annotations_with_documents(documents,mydb)
		
		print("Selecting subset of docs with annotations and high Altmetric scores (>%d) ..." % args.altmetricThreshold)
		annotated = [ d for d in documents if d['annotations']]
		annotated = remap_annotations(annotated)
		challenge_docs = [ d for d in documents if 'altmetric' in d and d['altmetric']['score'] > args.altmetricThreshold and not d['annotations'] ]
		
		for doc in challenge_docs:
			assert len(doc['annotations']) == 0
			
		print("Selected %d documents with annotations and %d \"challenge\" documents with high Altmetric scores" % (len(annotated),len(challenge_docs)))
		
		if args.mode == 'bestoutcome':
			print("Using ML to identify docs that can't be decided...")
			y_annotated, undecided_docs = get_y_and_undecided_docs(annotated,challenge_docs,args.posThreshold,args.negThreshold)
			print("Found %d decided and %d undecided documents" % (len(challenge_docs)-len(undecided_docs),len(undecided_docs)))
		
			print("Vectorizing annotated and undecided docs...")
			X_annotated, X_undecided = vectorizer_docs(annotated, undecided_docs)

			print("Search for optimal undecided document for annotation...")
		
			potential_outcomes = calculate_outcomes_of_different_document_choices(X_annotated,y_annotated,X_undecided,args.posThreshold)
			best_doc_change = potential_outcomes.mean(axis=1).max()
			best_doc_index = potential_outcomes.mean(axis=1).argmax()
			doc_to_annotate = undecided_docs[best_doc_index]
			dochash = hash(X_undecided.data.tobytes())
			current_coverage = round(1 - (len(undecided_docs) / len(challenge_docs)),3)
			print("Selected document (index=%d) with optimal outcome of %d" % (best_doc_index,best_doc_change))
		elif args.mode == 'popular':
			doc_to_annotate = sorted([ d for d in challenge_docs if 'altmetric' in d ],key=lambda x : x['altmetric']['score'])[-1]
			dochash = "popular"
			current_coverage = 0
			print("Selected document with score of %d" % (doc_to_annotate['altmetric']['score']))
			
		print("Title of paper: %s" % (doc_to_annotate['title']))
		print("URL of paper: %s" % (doc_to_annotate['url']))
		
		assert len(doc_to_annotate['annotations']) == 0
		
		if not 'document_id' in doc_to_annotate:
			print("Adding document to database")
			insert_document_into_db(mydb,doc_to_annotate)
		
		print("Adding document (id=%d) to active learning queue" % doc_to_annotate['document_id'])
		print("Coverage = %.3f" % current_coverage)
		add_doc_to_queue(mydb,doc_to_annotate,task_id,dochash,current_coverage)
	