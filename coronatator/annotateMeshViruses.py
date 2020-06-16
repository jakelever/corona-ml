import mysql.connector
from collections import OrderedDict
import csv
import json

def chunks(lst, n):
	"""Yield successive n-sized chunks from lst."""
	for i in range(0, len(lst), n):
		yield lst[i:i + n]
		
TASK_ID = 0

with open('alldocuments.json') as f:
	documents = json.load(f)
	
with open('local.json') as f:
	database = json.load(f)

mydb = mysql.connector.connect(
	host=database['host'],
	user=database['user'],
	passwd=database['passwd'],
	database=database['database']
)

mycursor = mydb.cursor()
	
sql = "SELECT document_id,pubmed_id,cord_uid FROM documents"
print(sql)
mycursor.execute(sql)
myresult = mycursor.fetchall()

pubmed_to_document_id = {}
cord_to_document_id = {}

pubmed_to_document_id = {str(pubmed_id):document_id for document_id,pubmed_id,cord_ui in myresult if pubmed_id }
cord_to_document_id = {cord_ui:document_id for document_id,pubmed_id,cord_ui in myresult if cord_ui }

print("Found %d Pubmed mappings" % len(pubmed_to_document_id))
print("Found %d CORD mappings" % len(cord_to_document_id))

virus_keywords = {}
virus_keywords['SARS-CoV-2'] = ['covid-19','covid 19','sars-cov-2','sars cov 2','sars-cov 2','sars cov-2','sars-cov2','sars cov2','sarscov2','2019-ncov','2019 ncov','ncov19','ncov-19','ncov 19','ncov2019','ncov-2019','ncov 2019']
virus_keywords['SARS-CoV'] = ['sars-cov','sars cov','sars-cov-1','sars cov 1','sars-cov 1','sars cov-1','sars-cov1','sars cov1','sarscov1','severe acute respiratory syndrome']
virus_keywords['MERS-CoV'] = ['mers-cov-2','mers cov 2','mers-cov 2','mers cov-2','mers cov2','mers-cov2','merscov2',]

autoannotations = []
for doc in documents:
	document_id = None
	if doc['cord_uid'] in cord_to_document_id:
		document_id = cord_to_document_id[doc['cord_uid']]
	elif doc['pubmed_id'] in pubmed_to_document_id:
		document_id = pubmed_to_document_id[doc['pubmed_id']]
	assert not document_id is None, "pubmed_id=%s, cord_uid=%s" % (doc['pubmed_id'],doc['cord_uid'])
	
	#if 'mesh' in doc:
	#	descriptors = [ heading[0][1] for heading in doc['mesh'] ]
	#	if 'Middle East Respiratory Syndrome Coronavirus' in descriptors:
	#		autoannotations.append((document_id,TASK_ID,'MERS-CoV'))
	#	if 'SARS Virus' in descriptors:
	#		autoannotations.append((document_id,TASK_ID,'SARS-CoV'))
	#	if 'Severe Acute Respiratory Syndrome' in descriptors:
	#		autoannotations.append((document_id,TASK_ID,'SARS-CoV'))
			

	combined_text = "%s\n%s" % (doc['title'],doc['abstract'])
	combined_text_lower = combined_text.lower()

	for virus in ['SARS-CoV-2','SARS-CoV','MERS-CoV']:
		for keyword in virus_keywords[virus]:
			if keyword in combined_text_lower:
				autoannotations.append((document_id,TASK_ID,virus))
				combined_text_lower = combined_text_lower.replace(keyword,'#'*10)
				

deletesql = "DELETE FROM autoannotations WHERE task_id='%d'" % TASK_ID
print(deletesql)
mycursor.execute(deletesql)

insertsql = "INSERT INTO autoannotations(document_id,task_id,annotation) VALUES (%s,%s,%s)"

autoannotations = sorted(set(autoannotations))
for chunk in chunks(autoannotations, 500):
	mycursor.executemany(insertsql, chunk)
	
print("Added %d annotations" % len(autoannotations))

mydb.commit()