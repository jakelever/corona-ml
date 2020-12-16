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
	print("time_per_item = %.4fs (%s)" % (time_per_item,nice_time(time_per_item)))
	print("remaining_items = %d" % remaining_items)
	print("time_so_far = %.1fs (%s)" % (time_so_far,nice_time(time_so_far)))
	print("remaining_time = %.1fs (%s)" % (remaining_time,nice_time(remaining_time)))
	print("total_time = %.1fs (%s)" % (total_time,nice_time(total_time)))
	print()
	
	
def getMultiScores(X_train,y_train,X_test):
	assert y_train.shape[1] > 1
	
	clf = OneVsRestClassifier(LogisticRegression(class_weight='balanced',random_state=0,C=21))

	clf.fit(X_train, y_train)
	
	scores = clf.predict_proba(X_test)
	
	return scores
	
def getScores(X_train,y_train,X_test):
	clf = LogisticRegression(class_weight='balanced',random_state=0,C=21)

	clf.fit(X_train, y_train)
	
	assert clf.classes_.tolist() == [0,1]
	
	scores = clf.predict_proba(X_test)[:,1]
	
	return scores
	
def searchForBestDocumentToAnnotate(X_annotated,y_annotated,X_undecided,posThreshold,show_time=True):
	start = time.time()

	X_annotated_plus_one = np.vstack([X_annotated,np.zeros((1,X_annotated.shape[1]))])
	
	outcomes = np.zeros((X_undecided.shape[0],y_annotated.shape[1]),dtype=np.int32)

	for docindex in range(X_undecided.shape[0]):
		if show_time and (docindex%10) == 0:
			outputTimeEstimates(docindex,X_undecided.shape[0],start)
			
		X_annotated_plus_one[X_annotated_plus_one.shape[0]-1,:] = X_undecided[docindex,:]
			
		neg_matrix = np.zeros((X_undecided.shape[0],y_annotated.shape[1]))
		for label_index in range(y_annotated.shape[1]):
			y_with_artifical_addition = np.concatenate([y_annotated[:,label_index],[0]])
			neg_scores = getScores(X_annotated_plus_one, y_with_artifical_addition, X_undecided)
			neg_matrix[:,label_index] = neg_scores
		
		for label_index in range(y_annotated.shape[1]):
			y_with_artifical_addition = np.concatenate([y_annotated[:,label_index],[1]])
			pos_scores = getScores(X_annotated_plus_one, y_with_artifical_addition, X_undecided)
			
			pos_matrix = neg_matrix.copy()
			pos_matrix[:,label_index] = pos_scores
			
			numHasHighConfPositive = int(sum(pos_matrix.max(axis=1) > posThreshold))
			outcomes[docindex,label_index] = numHasHighConfPositive

		#outcomes[docindex,0] = numHighConfNegative
		#outcomes[docindex,1] = numHighConfPositive
		#outcomes[iteration,0] = numHighConf
			
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

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Prepare data for active learning')
	#parser.add_argument('--db',required=True,type=str,help='JSON with database settings')
	parser.add_argument('--inDir',required=True,type=str,help='Output dir to put matrices')
	parser.add_argument('--negThreshold',required=False,default=0.3,type=float,help='Threshold below which is a confident negative (default=0.25)')
	parser.add_argument('--posThreshold',required=False,default=0.7,type=float,help='Threshold above which is a confident positive (default=0.75)')
	#parser.add_argument('--outFile',required=True,type=str,help='Output file')
	
	args = parser.parse_args()
	
	X_annotated = np.load(os.path.join(args.inDir,'X_annotated.npy'))
	y_annotated = np.load(os.path.join(args.inDir,'y_annotated.npy'))
	X_undecided = np.load(os.path.join(args.inDir,'X_undecided.npy'))
	undecided_scores = np.load(os.path.join(args.inDir,'undecided_scores.npy'))
	
	with open(os.path.join(args.inDir,'undecided_docs.pickle'),'rb') as f:
		undecided_docs = pickle.load(f)
		
	if False:
		with open(args.db) as f:
			database = json.load(f)
			
		mydb = mysql.connector.connect(
			host=database['host'],
			user=database['user'],
			passwd=database['passwd'],
			database=database['database']
		)
		mycursor = mydb.cursor()
	
		#loadDocumentIDMapping(mycursor,undecided_docs)
	
	#baselineConfNumber = getConfidenceNumbers(X_annotated,y_annotated[:,args.label_index],X_undecided,args.posThreshold,args.negThreshold)
	#print("baselineConfNumber=",baselineConfNumber)
	
	#outcomes = searchForBestDocumentToAnnotate(X_annotated,y_annotated,X_undecided,args.posThreshold)
	
	current_y = np.copy(y_annotated)
	current_train_X = np.copy(X_annotated)
	current_unknown_X = np.copy(X_undecided)

	num_iter = current_unknown_X.shape[0]
	prev_done = []
	start_time = time.time()
	for i in range(num_iter):
	
		multi_scores = getMultiScores(current_train_X, current_y, current_unknown_X)
		
		np.savetxt('multi_scores_%04d.csv' % i, multi_scores, delimiter=',', fmt="%f")
		
		min_scores = multi_scores.min(axis=1)
		min_score_percentiles = stats.rankdata(min_scores,"average") / min_scores.shape[0]
		#print(min_score_percentiles.shape)
		#print(min_score_percentiles[409])
		
		current_outcomes = searchForBestDocumentToAnnotate(current_train_X,current_y,current_unknown_X,args.posThreshold,show_time=False)
		
		for j in prev_done:
			current_outcomes[j,:] = -1
			
		np.savetxt('current_outcomes_%04d.csv' % i, current_outcomes, delimiter=',', fmt="%d")
		
		best_doc_change = current_outcomes.min(axis=1).max()
		best_doc_index = current_outcomes.min(axis=1).argmax()
		best_min_score_percentile = min_score_percentiles[best_doc_index]
		print("# best_doc_index=%d, best_doc_change=%d, train_size=%d" % (best_doc_index,best_doc_change,current_train_X.shape[0]))
		print("# best_min_score_percentile = %f" % best_min_score_percentile)
		
		which_label_was_min = current_outcomes[best_doc_index,:].argmin()
		label_score_percentiles = stats.rankdata(multi_scores[:,which_label_was_min],"average") / multi_scores.shape[0]
		
		label_score_percentile_for_doc = label_score_percentiles[best_doc_index]
		
		num_where_label_was_min = (current_outcomes.min(axis=1) == current_outcomes[:,which_label_was_min]).sum()
		
		print("which_label_was_min = %d" % which_label_was_min)
		print("num_where_label_was_min = %d/%d (%.1f%%)" % (num_where_label_was_min,current_outcomes.shape[0],100*num_where_label_was_min/current_outcomes.shape[0]))
		print("label_score_percentile_for_doc = %f" % label_score_percentile_for_doc)
		
		prev_done.append(best_doc_index)
		
		current_train_X = np.vstack([current_train_X,current_unknown_X[best_doc_index,:]])
		#current_unknown_X = np.delete(current_unknown_X,best_doc_index,0)
		
		current_y = np.vstack([current_y,np.zeros((1,current_y.shape[1]))])
		current_y[current_y.shape[0]-1,current_outcomes[best_doc_index,:].argmax()] = 1
		
		outputTimeEstimates(i,num_iter,start_time)
		#break

		
	np.savetxt('undecided_scores.csv', undecided_scores, delimiter=',', fmt="%f")
	
	
	