import json
import mysql.connector
from collections import defaultdict,Counter
import sklearn.metrics
import matplotlib.pyplot as plt
import seaborn as sn
import pandas as pd
import numpy as np
	
import nltk
from nltk.corpus import stopwords
from IPython.display import HTML, display
import tabulate
import itertools

from .language import detect_language,filter_languages
from .documentvectorizer import DocumentVectorizer
from .ner import tag_documents,tag_entities


def dbconnect():
	mydb = mysql.connector.connect(
	  host="localhost",
	  user="root",
	  passwd="",
	  database="potator"
	)
	return mydb
	
def get_annotations(mydb,task_ids=None):
	if task_ids is None:
		sql = "SELECT d.cord_uid as cord_uid, d.pubmed_id as pubmed_id, ao.name as name FROM documents d, annotations a, annotationoptions ao WHERE d.document_id = a.document_id AND a.annotationoption_id = ao.annotationoption_id"
	else:
		assert isinstance(task_ids,list)
		task_ids = ",".join(map(str,map(int,task_ids)))
		sql = "SELECT d.cord_uid as cord_uid, d.pubmed_id as pubmed_id, ao.name as name FROM documents d, annotations a, annotationoptions ao WHERE d.document_id = a.document_id AND a.annotationoption_id = ao.annotationoption_id AND ao.task_id IN (%s)" % task_ids
	
	mycursor = mydb.cursor()
	mycursor.execute(sql)
	myresult = mycursor.fetchall()

	annotations_by_cord = defaultdict(set)
	annotations_by_pubmed_id = defaultdict(set)
	for cord_uid,pubmed_id,annotation in myresult:
		if cord_uid:
			annotations_by_cord[cord_uid].add(annotation)
		if pubmed_id:
			annotations_by_pubmed_id[str(pubmed_id)].add(annotation)
			
	return annotations_by_cord, annotations_by_pubmed_id
	
def load_documents(filename):
	with open(filename) as f:
		documents = json.load(f)
	return documents
	
	
def associated_annotations_with_documents(documents,mydb,task_ids=None):
	annotations_by_cord, annotations_by_pubmed_id = get_annotations(mydb,task_ids)
	
	for doc in documents:
		cord_uid = doc['cord_uid']
		pubmed_id = doc['pubmed_id']
		doc['annotations'] = set()
		if cord_uid in annotations_by_cord:
			doc['annotations'].update(annotations_by_cord[cord_uid])
		if pubmed_id in annotations_by_pubmed_id:
			doc['annotations'].update(annotations_by_pubmed_id[pubmed_id])
		doc['annotations'] = sorted(list(doc['annotations']))
		
	return documents
	
def load_documents_with_annotations(filename,mydb,task_ids=None):
	documents = load_documents(filename)
	documents = associated_annotations_with_documents(documents,mydb,task_ids)
			
	return documents
	
def chunks(lst, n):
	"""Yield successive n-sized chunks from lst."""
	for i in range(0, len(lst), n):
		yield lst[i:i + n]
	
def draw_confusion_matrix(actual,predicted):
	if isinstance(actual,np.ndarray):
		actual = actual.flatten().tolist()
	if isinstance(predicted,np.ndarray):
		predicted = predicted.flatten().tolist()
	assert isinstance(actual,list)
	assert isinstance(predicted,list)
	assert len(actual) == len(predicted)
	
	classes = sorted(set(actual+predicted))
	confusion_matrix = sklearn.metrics.confusion_matrix(actual,predicted,labels=classes)

	df_cm = pd.DataFrame(confusion_matrix, index = classes,
					  columns = classes)
	plt.figure(figsize = (10,7))
	sn.heatmap(df_cm, annot=True, fmt='g')
	plt.ylabel('Actual')
	plt.xlabel('Predicted')
	
def draw_pseudo_confusion_matrix(actual,predicted,labels):
	assert actual.shape == predicted.shape
	assert isinstance(labels,list)
	
	pseudo_confusion_matrix = np.zeros((len(labels),len(labels)+1))
	no_label_index = len(labels)
	for i in range(actual.shape[0]):
		g = actual[i,:]
		p = predicted[i,:]
		
		gold_labels = g.nonzero()[0].tolist()
		pred_labels = p.nonzero()[0].tolist()
		
		for gold_label,pred_label in itertools.product(gold_labels,pred_labels):
			if gold_label == pred_label:
				pseudo_confusion_matrix[gold_label,gold_label] += 1
			elif pred_label in gold_labels:
				pass
			else:
				pseudo_confusion_matrix[gold_label,pred_label] += 1
				
		if len(pred_labels) == 0:
			for gold_label in gold_labels:
				pseudo_confusion_matrix[gold_label,no_label_index] += 1

	df_cm = pd.DataFrame(pseudo_confusion_matrix, index = labels, columns = labels + ['No Label'])
	plt.figure(figsize = (10,7))
	sn.heatmap(df_cm, annot=True, fmt='g')
	plt.ylabel('Actual')
	plt.xlabel('Predicted')
	
def draw_table(data):
	display(HTML(tabulate.tabulate(data, tablefmt='html')))