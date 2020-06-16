import mysql.connector
from collections import OrderedDict
import csv
import json

def chunks(lst, n):
	"""Yield successive n-sized chunks from lst."""
	for i in range(0, len(lst), n):
		yield lst[i:i + n]
		
TASK_ID = 1

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

chemicalSkips = {"Anti-Inflammatory Agents","Antiviral Agents","Anti-Bacterial Agents","Anti-Infective Agents","Antioxidants","Ligands","Drug Combinations"}

autoannotations = []
for doc in documents:
	document_id = None
	if doc['cord_uid'] in cord_to_document_id:
		document_id = cord_to_document_id[doc['cord_uid']]
	elif doc['pubmed_id'] in pubmed_to_document_id:
		document_id = pubmed_to_document_id[doc['pubmed_id']]
	assert not document_id is None, "pubmed_id=%s, cord_uid=%s" % (doc['pubmed_id'],doc['cord_uid'])
	
	isDrugRepurposing = False
	if 'mesh' in doc:
		descriptorsOnly = [ heading[0][1] for heading in doc['mesh'] ]
		qualifiersOnly = [ q[1] for heading in doc['mesh'] for q in heading[1:] ]
			
		if 'drug therapy' in qualifiersOnly:
			isDrugRepurposing = True
		if 'drug effects' in qualifiersOnly:
			isDrugRepurposing = True
		if 'pharmacology' in qualifiersOnly:
			isDrugRepurposing = True
		if 'therapy' in qualifiersOnly:
			isDrugRepurposing = True
		if 'Drug Design' in descriptorsOnly:
			isDrugRepurposing = False
			
	hasChemicals = False
	if 'chemicals' in doc:
		chemicals = [ c[1] for c in doc['chemicals'] ]
		chemicals = [ c for c in chemicals if not c in chemicalSkips ]
		hasChemicals = len(chemicals) > 0
		
	
	ignoredPubType = True
	if 'pub_type' in doc:
		ignoredPubType = any( p in doc['pub_type'] for p in ['Editorial','News','Comment'] )
			
	if isDrugRepurposing and hasChemicals and not ignoredPubType:
		autoannotations.append((document_id,TASK_ID,'repurposing'))
			

deletesql = "DELETE FROM autoannotations WHERE task_id='%d'" % TASK_ID
print(deletesql)
mycursor.execute(deletesql)

insertsql = "INSERT INTO autoannotations(document_id,task_id,annotation) VALUES (%s,%s,%s)"

autoannotations = sorted(set(autoannotations))
for chunk in chunks(autoannotations, 500):
	mycursor.executemany(insertsql, chunk)
	
print("Added %d annotations" % len(autoannotations))

mydb.commit()