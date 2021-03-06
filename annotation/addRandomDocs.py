import mysql.connector
import json
import argparse
import random

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
			
def insert_document_into_db(mydb,doc,phase):
	mycursor = mydb.cursor()
	
	columns = [ 'pubmed_id', 'cord_uid', 'title', 'abstract', 'publish_year', 'journal', 'url' ]
	
	if doc['pubmed_id']:
		doc['url'] = "https://pubmed.ncbi.nlm.nih.gov/%s" % doc['pubmed_id']
	elif doc['doi']:
		doc['url'] = "https://doi.org/%s" % doc['doi']
	else:
		urls = [ u.strip() for u in doc['url'].split(';') ]
		doc['url'] = urls[0]
	
	record = [ doc[c] for c in columns ] + [ phase ]
	
	insertsql = "INSERT INTO documents (%s,phase,added) VALUES (%s,%%s,NOW())" % (",".join(columns),",".join([ '%s' for _ in columns ]))
	
	mycursor.execute(insertsql, record)
	#mydb.commit()
	
	doc['document_id'] = mycursor.lastrowid

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Prepare data for active learning')
	parser.add_argument('--db',required=True,type=str,help='JSON with database settings')
	parser.add_argument('--inDocs',required=True,type=str,help='Input file with all the documents')
	args = parser.parse_args()
	
	mydb = connect_db(args.db)
	
	print("Loading all documents with database IDs and getting Altmetric data...")
	with open(args.inDocs) as f:
		documents = json.load(f)
	load_document_id_mapping(mydb, documents)
	
	print("Loaded %d documents" % len(documents))
	print("%d documents are already in DB" % len( [ d for d in documents if 'document_id' in d ] ) )
	
	new_documents = [ d for d in documents if not 'document_id' in d ]
	
	print("%d documents are not in DB" % len( new_documents ) )
	
	random.shuffle(new_documents)
	
	search = new_documents[:500]
	
	print("Adding documents to database")
	for doc_to_add in search:
		insert_document_into_db(mydb,doc_to_add,'phase4')

	print("Added %d documents" % len(search))
	
