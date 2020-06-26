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
	columns['publish_year'] = 'INT'
	columns['publish_month'] = 'INT'
	columns['publish_day'] = 'INT'
	columns['title'] = 'TEXT'
	#if (args.db == 'local'):
	columns['abstract'] = 'TEXT'
	columns['journal'] = 'TEXT'
	columns['url'] = 'VARCHAR(255)'
	columns['mesh'] = 'TEXT NULL'
	columns['has_mesh'] = 'BOOLEAN'
	columns['chemicals'] = 'TEXT NULL'
	columns['pub_type'] = 'TEXT NULL'

	dbfields = ",".join(columns.keys())
	dbvalues = ",".join('%s' for _ in columns.keys())
	insertsql = "INSERT INTO documents (%s) VALUES (%s)" % (dbfields,dbvalues)
	print(insertsql)

	dbfieldsandvalues = ",".join('%s=%%s' % k for k in columns.keys())
	updatesql = "UPDATE documents SET %s WHERE document_id='%%s'" % (dbfieldsandvalues)
	print(updatesql)

	#assert False
		
	insertrecords = []
	updaterecords = []
	for doc in documents:
		#if doc['abstract'].lower().startswith('abstract'):
		#	doc['abstract'] = doc['abstract'][len('abstract'):].strip()
		if args.db == 'remote' and not '-cov' in doc['abstract'].lower():
			continue
		
		if 'publish_time' in doc:
			assert len(doc['publish_time']) in [0,4,10], doc['publish_time']
			doc['publish_year'] = None
			doc['publish_month'] = None
			doc['publish_day'] = None
			if len(doc['publish_time']) == 4:
				doc['publish_year'] = doc['publish_time']
			elif len(doc['publish_time']) == 10:
				doc['publish_year'] = doc['publish_time'][0:4]
				doc['publish_month'] = doc['publish_time'][5:7]
				doc['publish_day'] = doc['publish_time'][8:10]
				
		if 'mesh' in doc:
			mesh_txts = []
			for heading in doc['mesh']:
				mesh_txt = "/".join( mesh_name + ('*' if is_major=='Y' else '') for mesh_id,mesh_name,is_major in heading )
				mesh_txts.append(mesh_txt)
			doc['mesh'] = " | ".join(sorted(mesh_txts))
			doc['has_mesh'] = True
		else:
			doc['mesh'] = None
			doc['has_mesh'] = False
			
		if 'chemicals' in doc:
			chemical_txts = [ mesh_name for mesh_id,mesh_name in doc['chemicals'] ]
			doc['chemicals'] = " | ".join(sorted(chemical_txts))
		else:
			doc['chemicals'] = None
			
		if 'pub_type' in doc:
			doc['pub_type'] = " | ".join(sorted(doc['pub_type']))
		else:
			doc['pub_type'] = None
			
		#assert False
		
		record = [ doc[c] for c in columns.keys() ]
		
		if doc['cord_uid'] in cord_to_document_id:
			document_id = cord_to_document_id[doc['cord_uid']]
			record.append(document_id)
			updaterecords.append(record)
		elif doc['pubmed_id'] in pubmed_to_document_id:
			document_id = pubmed_to_document_id[doc['pubmed_id']]
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
		
	mydb.commit()
	print("Added %d documents" % len(insertrecords))
	print("Updated %d documents" % len(updaterecords))