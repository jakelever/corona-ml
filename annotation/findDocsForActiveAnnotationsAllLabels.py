import sys
sys.path.append("../pipeline")

import mysql.connector
import pickle
import argparse
import json
import itertools
from collections import defaultdict,Counter
from collections.abc import Iterable
import numpy as np
import time
import os
from scipy import stats

from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.decomposition import TruncatedSVD

def nice_time(seconds):
	days = int(seconds) // (24*60*60)
	seconds -= days * (24*60*60)
	hours = int(seconds) // (60*60)
	seconds -= hours * (60*60)
	minutes = int(seconds) // (60)
	seconds -= minutes * (60)
	
	bits = []
	if days:
		bits.append( "1 day" if days == 1  else "%d days" % days)
	if hours:
		bits.append( "1 hour" if hours == 1 else "%d hours" % hours)
	if minutes:
		bits.append( "1 minute" if minutes == 1 else "%d minutes" % minutes)
	bits.append( "1 second" if seconds == 1 else "%.1f seconds" % seconds)
	
	return ", ".join(bits)
	
def outputTimeEstimates(index,total_count,start_time):
	now = time.time()
	perc = 100*(index+1)/total_count

	time_so_far = (now-start_time)
	time_per_item = time_so_far / (index+1)
	remaining_items = total_count - index
	remaining_time = time_per_item * remaining_items
	total_time = time_so_far + remaining_time

	print("%.1f%% (%d/%d)" % (perc,index+1,total_count))
	print("time_per_item = %.4fs" % time_per_item)
	print("remaining_items = %d" % remaining_items)
	print("time_so_far = %.1fs (%s)" % (time_so_far,nice_time(time_so_far)))
	print("remaining_time = %.1fs (%s)" % (remaining_time,nice_time(remaining_time)))
	print("total_time = %.1fs (%s)" % (total_time,nice_time(total_time)))
	print()
	
def getConfidenceNumbers(X_train,y_train,X_test,posThreshold,negThreshold):
	clf = OneVsRestClassifier(LogisticRegression(class_weight='balanced',random_state=0,C=21))

	clf.fit(X_train, y_train)
	
	#assert clf.classes_.tolist() == [0,1]
	
	scores = clf.predict_proba(X_test)

	numHasHighConfPositive = int(sum(scores.max(axis=1) > posThreshold))
	
	return numHasHighConfPositive
	
def searchForBestDocumentToAnnotate(X_annotated,y_annotated,X_undecided,posThreshold,negThreshold,show_time=True):
	num_samples = X_annotated.shape[0]
	num_labels = y_annotated.shape[1]

	start = time.time()

	X_annotated_plus_one = np.vstack([X_annotated,np.zeros((1,X_annotated.shape[1]))])
	
	outcomes = np.zeros((num_samples,num_labels),dtype=np.int32)
	
	y_with_artifical_addition = np.concatenate([y_annotated,np.zeros((1,y_annotated.shape[1]))])
		

	for docindex in range(X_undecided.shape[0]):
		#if show_time and (docindex%10) == 0:
		outputTimeEstimates(docindex,num_samples,start)
				
		X_annotated_plus_one[X_annotated_plus_one.shape[0]-1,:] = X_undecided[docindex,:]
			
		for label_index in range(y_annotated.shape[1]):
		
			y_with_artifical_addition[y_with_artifical_addition.shape[0]-1,:] = 0
			y_with_artifical_addition[y_with_artifical_addition.shape[0]-1,label_index] = 1

			numHighConf = getConfidenceNumbers(X_annotated_plus_one, y_with_artifical_addition,X_undecided,posThreshold,negThreshold)

			outcomes[docindex,label_index] = numHighConf
			
		#break
			
	if show_time:
		outputTimeEstimates(X_undecided.shape[0]-1,X_undecided.shape[0],start)
			
	return outcomes
	
def loadDocumentIDMapping(mycursor,undecided_docs):
	sql = "SELECT document_id,pubmed_id,cord_uid FROM documents"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()

	pubmed_to_document_id = {}
	cord_to_document_id = {}

	pubmed_to_document_id = {str(pubmed_id):document_id for document_id,pubmed_id,cord_ui in myresult if pubmed_id }
	cord_to_document_id = {cord_ui:document_id for document_id,pubmed_id,cord_ui in myresult if cord_ui }
	
	for d in undecided_docs:
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
	
def getBestDocumentForAnnotation(X_annotated,y_annotated,X_undecided,undecided_scores,undecided_docs):
	
	
	#negOutcomes = searchForBestDocumentToAnnotate(candidate_doc_indices,X_annotated,y_annotated,X_undecided,args.label_index,0,args.posThreshold,args.negThreshold,show_time=True)
	posOutcomes = searchForBestDocumentToAnnotate(candidate_doc_indices,X_annotated,y_annotated,X_undecided,args.label_index,1,args.posThreshold,args.negThreshold,show_time=True)
	outcomes = np.hstack([negOutcomes,posOutcomes])
	
	best_row = outcomes.min(axis=1).argmax()
	best_doc_index = candidate_doc_indices[best_row]
	best_outcome = outcomes.min(axis=1)[best_row]
	
	associated_prob = probsForThisLabel[best_doc_index]
	
	print(best_doc_index,associated_prob,best_outcome)
	
	best_doc = undecided_docs[best_doc_index]
	
	return best_doc_index

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Prepare data for active learning')
	parser.add_argument('--db',required=True,type=str,help='JSON with database settings')
	parser.add_argument('--inDir',required=True,type=str,help='Output dir to put matrices')
	parser.add_argument('--negThreshold',required=False,default=0.25,type=float,help='Threshold below which is a confident negative (default=0.25)')
	parser.add_argument('--posThreshold',required=False,default=0.75,type=float,help='Threshold above which is a confident positive (default=0.75)')
	#parser.add_argument('--outFile',required=True,type=str,help='Output file')
	
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
	
	X_annotated = np.load(os.path.join(args.inDir,'X_annotated.npy'))
	y_annotated = np.load(os.path.join(args.inDir,'y_annotated.npy'))
	X_undecided = np.load(os.path.join(args.inDir,'X_undecided.npy'))
	undecided_scores = np.load(os.path.join(args.inDir,'undecided_scores.npy'))
	
	with open(os.path.join(args.inDir,'undecided_docs.pickle'),'rb') as f:
		undecided_docs = pickle.load(f)
		
	loadDocumentIDMapping(mycursor,undecided_docs)
	
	baselineConfNumber = getConfidenceNumbers(X_annotated,y_annotated,X_undecided,args.posThreshold,args.negThreshold)
	print("baselineConfNumber=",baselineConfNumber)
	
	#chosenDoc = getBestDocumentForAnnotation(X_annotated,y_annotated,X_undecided,undecided_scores,undecided_docs)
	
	np.savetxt('scores.csv', undecided_scores, delimiter=',', fmt="%f")
	
	outcomes = searchForBestDocumentToAnnotate(X_annotated,y_annotated,X_undecided,args.posThreshold,args.negThreshold)
	
	np.savetxt('outcomes.csv', outcomes, delimiter=',', fmt="%d")