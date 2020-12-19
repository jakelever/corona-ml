import mysql.connector
from collections import OrderedDict
import csv
import json
import argparse

def chunks(lst, n):
	"""Yield successive n-sized chunks from lst."""
	for i in range(0, len(lst), n):
		yield lst[i:i + n]
		
if __name__ == '__main__':
	parser = argparse.ArgumentParser('Load documents into database')
	parser.add_argument('--json',required=True,type=str,help='JSON file with annotations')
	parser.add_argument('--db',required=True,type=str,help='JSON with database settings')
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

		
	sql = "SELECT document_id,pubmed_id,cord_uid FROM documents"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()

	pubmed_to_document_id = {}
	cord_to_document_id = {}

	all_db_document_ids = [ document_id for document_id,pubmed_id,cord_ui in myresult ]
	pubmed_to_document_id = {str(pubmed_id):document_id for document_id,pubmed_id,cord_ui in myresult if pubmed_id }
	cord_to_document_id = {cord_ui:document_id for document_id,pubmed_id,cord_ui in myresult if cord_ui }

	print("Found %d Pubmed mappings" % len(pubmed_to_document_id))
	print("Found %d CORD mappings" % len(cord_to_document_id))

	#for record in myresult:
	#	document_id,pubmed_id,cord_ui = record
	#	assert pubmed_id or cord_ui
		#break

	#assert False

	with open(args.json) as f:
		documents = json.load(f)
		
	columns = OrderedDict()
	#columns['document_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['pubmed_id'] = 'INT NULL'
	columns['cord_uid'] = 'VARCHAR(255) NULL'
	columns['doi'] = 'VARCHAR(255) NULL'
	columns['pmcid'] = 'INT NULL'
	columns['publish_year'] = 'INT'
	columns['publish_month'] = 'INT'
	columns['publish_day'] = 'INT'
	columns['title'] = 'TEXT'
	columns['abstract'] = 'TEXT'
	columns['journal'] = 'TEXT'
	columns['url'] = 'VARCHAR(255)'
	columns['is_preprint'] = 'BOOL'

	dbfields = ",".join(columns.keys())
	dbvalues = ",".join('%s' for _ in columns.keys())
	insertsql = "INSERT INTO documents (%s) VALUES (%s)" % (dbfields,dbvalues)
	print(insertsql)

	dbfieldsandvalues = ",".join('%s=%%s' % k for k in columns.keys())
	updatesql = "UPDATE documents SET %s WHERE document_id='%%s'" % (dbfieldsandvalues)
	print(updatesql)

	deletesql = "DELETE FROM documents WHERE document_id = '%s'"
	#assert False
		
	seen_document_ids = []
	insertrecords = []
	updaterecords = []
	for doc in documents:
		if not doc['pubmed_id']:
			doc['pubmed_id'] = None
		if not doc['cord_uid']:
			doc['cord_uid'] = None
		if not doc['pmcid']:
			doc['pmcid'] = None
		
		record = [ doc[c] for c in columns.keys() ]
		
		if doc['cord_uid'] in cord_to_document_id:
			document_id = cord_to_document_id[doc['cord_uid']]
			seen_document_ids.append(document_id)
			record.append(document_id)
			updaterecords.append(record)
		elif doc['pubmed_id'] in pubmed_to_document_id:
			document_id = pubmed_to_document_id[doc['pubmed_id']]
			seen_document_ids.append(document_id)
			record.append(document_id)
			updaterecords.append(record)
		else:
			#print(doc['cord_uid'],doc['pubmed_id'])
			insertrecords.append(record)
		#mycursor.execute(sql,record)
		
		
	for chunk in chunks(insertrecords, 500):
		mycursor.executemany(insertsql, chunk)
		#break
	
	for chunk in chunks(updaterecords, 500):
		mycursor.executemany(updatesql, chunk)
	
	never_seen_document_ids = [ [document_id] for document_id in all_db_document_ids if not document_id in seen_document_ids ]
	
	for chunk in chunks(never_seen_document_ids, 500):
		mycursor.executemany(deletesql, chunk)
		
	mydb.commit()
	print("Added %d documents" % len(insertrecords))
	print("Updated %d documents" % len(updaterecords))
	print("Deleting %d documents not found in input file" % len(never_seen_document_ids))