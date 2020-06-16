import mysql.connector
from collections import OrderedDict
import csv
import json
import random
import re
import argparse

def chunks(lst, n):
	"""Yield successive n-sized chunks from lst."""
	for i in range(0, len(lst), n):
		yield lst[i:i + n]

with open('local-coronahub.json') as f:
	database = json.load(f)

mydb = mysql.connector.connect(
	host=database['host'],
	user=database['user'],
	passwd=database['passwd'],
	database=database['database']
)

mycursor = mydb.cursor()

with open('predictions.json') as f:
	documents = json.load(f)

	
entities = []
entities += sorted(set( ('drug',drug_name) for doc in documents for drug_name in doc['drugs'] ))
entity_to_id = {}
for entity_type,entity_name in entities:
	insert_entity_sql = "INSERT INTO entities(name,type) VALUES (%s,%s)"
	mycursor.execute(insert_entity_sql,[entity_name,entity_type])
	entity_id = mycursor.lastrowid
	entity_to_id[(entity_type,entity_name)] = entity_id
	
topics = sorted(set( sum( (doc['predictions'] for doc in documents), []) ))
topic_to_id = {}
for topic_name in topics:
	insert_topic_sql = "INSERT INTO topics(name) VALUES (%s)"
	mycursor.execute(insert_topic_sql,[topic_name])
	topic_id = mycursor.lastrowid
	topic_to_id[topic_name] = topic_id


doc_columns = ['pubmed_id','cord_uid','title','abstract','publish_year','journal','url','sars_cov_1','sars_cov_2','mers_cov']
dbfields = ",".join(doc_columns)
dbvalues = ",".join('%s' for _ in doc_columns)
insert_doc_sql = "INSERT INTO documents (%s) VALUES (%s)" % (dbfields,dbvalues)

for docno,doc in enumerate(documents):
	if docno % 1000 == 0:
		print("Adding %d" % docno)
	
	doc['sars_cov_1'] = 'SARS-CoV' in doc['viruses']
	doc['sars_cov_2'] = 'SARS-CoV-2' in doc['viruses']
	doc['mers_cov'] = 'MERS-CoV' in doc['viruses']
	
	record = [ doc[c] for c in doc_columns ]

	mycursor.execute(insert_doc_sql,record)
	document_id = mycursor.lastrowid
	
	for topic_name in doc['predictions']:
		insert_topicannotation_sql = "INSERT INTO topicannotations(document_id,topic_id) VALUES (%s,%s)"
		topic_id = topic_to_id[topic_name]
		mycursor.execute(insert_topicannotation_sql,[document_id,topic_id])
	
	for drug_name in doc['drugs']:
		insert_entityannotation_sql = "INSERT INTO entityannotations(document_id,entity_id) VALUES (%s,%s)"
		entity_id = entity_to_id[('drug',drug_name)]
		mycursor.execute(insert_entityannotation_sql,[document_id,entity_id])

mydb.commit()
