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
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Add or update documents in the database')
	parser.add_argument('--db',required=True,type=str,help='JSON with database settings')
	parser.add_argument('--inDocs',required=True,type=str,help='Input file with all the documents')
	parser.add_argument('--addcount',required=False,default=0,type=int,help='')
	args = parser.parse_args()
	
	mydb = connect_db(args.db)
	mycursor = mydb.cursor()

	sql = "SELECT document_id,pubmed_id,cord_uid FROM documents"
	#print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()

	pubmed_to_document_id = {}
	cord_to_document_id = {}

	pubmed_to_document_id = {str(pubmed_id):document_id for document_id,pubmed_id,cord_ui in myresult if pubmed_id }
	cord_to_document_id = {cord_ui:document_id for document_id,pubmed_id,cord_ui in myresult if cord_ui }

	#print("Found %d Pubmed mappings" % len(pubmed_to_document_id))
	#print("Found %d CORD mappings" % len(cord_to_document_id))

	with open(args.inDocs) as f:
		documents = json.load(f)
		
	columns = OrderedDict()
	columns['pubmed_id'] = 'INT NULL'
	columns['cord_uid'] = 'VARCHAR(255) NULL'
	columns['title'] = 'TEXT'
	columns['abstract'] = 'TEXT'
	columns['publish_year'] = 'INT'
	columns['journal'] = 'TEXT'
	columns['url'] = 'VARCHAR(255)'

	dbfields = ",".join(columns.keys())
	dbvalues = ",".join('%s' for _ in columns.keys())
	insertsql = "INSERT INTO documents (%s) VALUES (%s)" % (dbfields,dbvalues)
	#print(insertsql)

	dbfieldsandvalues = ",".join('%s=%%s' % k for k in columns.keys())
	updatesql = "UPDATE documents SET %s WHERE document_id='%%s'" % (dbfieldsandvalues)
	print(updatesql)

	virus_keywords = {}
	virus_keywords['SARS-CoV-2'] = ['covid','covid-19','covid 19','sars-cov-2','sars cov 2','sars-cov 2','sars cov-2','sars-cov2','sars cov2','sarscov2','2019-ncov','2019 ncov','ncov19','ncov-19','ncov 19','ncov2019','ncov-2019','ncov 2019','(sars)-cov-2','(sars) cov 2','(sars)-cov 2','(sars) cov-2','(sars)-cov2','(sars) cov2','(sars)cov2']
	virus_keywords['SARS-CoV'] = ['sars','sars-cov','sars cov','sars-cov-1','sars cov 1','sars-cov 1','sars cov-1','sars-cov1','sars cov1','sarscov1','severe acute respiratory syndrome', '(sars)-cov','(sars) cov','(sars)-cov-1','(sars) cov 1','(sars)-cov 1','(sars) cov-1','(sars)-cov1','(sars) cov1','(sars)cov1', 'sars virus']
	virus_keywords['MERS-CoV'] = ['mers','middle east respiratory syndrome','mers-cov','mers cov','mers-cov','mers cov','mers cov','mers-cov','merscov','(mers)-cov','(mers) cov','(mers)-cov','(mers) cov','(mers) cov','(mers)-cov','(mers)cov','mers virus']
		
	#emptyAbstractCount,hasPDFParse,hasPMCParse = 0,0,0

	virus_re = []
	for virus,keywords in virus_keywords.items():
		virus_re += [ re.compile(r"\b%s\b" % re.escape(keyword)) for keyword in keywords ]
		
	unique_titles = set()
		
	insertrecords = []
	updaterecords = []
	for doc in documents:
		#if 'source_x' in doc and doc['journal'].strip() == '':
		#	print("\t".join([doc['source_x'],doc['journal']]))
		#continue
			
		if doc['abstract'].lower().startswith('abstract'):
			doc['abstract'] = doc['abstract'][len('abstract'):].lstrip(':.')
		doc['abstract'] = doc['abstract'].strip()
		
		if 'journaliso' in doc:
			doc['journal'] = doc['journaliso']
			
		if 'source_x' in doc and doc['source_x'] in ['biorxiv','medrxiv']:
			doc['journal'] = doc['source_x']
		
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
				
		#print('adding')
		record = [ doc[c] for c in columns.keys() ]
		
		if doc['cord_uid'] in cord_to_document_id:
			document_id = cord_to_document_id[doc['cord_uid']]
			record.append(document_id)
			updaterecords.append(record)
			continue
		elif doc['pubmed_id'] in pubmed_to_document_id:
			document_id = pubmed_to_document_id[doc['pubmed_id']]
			record.append(document_id)
			updaterecords.append(record)
			continue
			
		if not args.addcount:
			continue
			
		if doc['abstract'] == '':
			continue
			#emptyAbstractCount += 1
			#if 'has_pdf_parse' in doc and doc['has_pdf_parse'] == 'True':
			#	hasPDFParse += 1
			#if 'has_pmc_xml_parse' in doc and doc['has_pmc_xml_parse'] == 'True':
			#	hasPMCParse += 1
			
		if doc['title'] in unique_titles:
			continue
		unique_titles.add(doc['title'])
					
		
		addDoc = False
		
		if 'mesh' in doc:
			descriptors = [ heading[0][1] for heading in doc['mesh'] ]
			if 'Middle East Respiratory Syndrome Coronavirus' in descriptors:
				addDoc = True
			if 'SARS Virus' in descriptors:
				addDoc = True
			if 'Severe Acute Respiratory Syndrome' in descriptors:
				addDoc = True
				
				
		combined_text = "%s\n%s" % (doc['title'],doc['abstract'])
		combined_text_lower = combined_text.lower()
					
		if not addDoc and any (regex.search(combined_text_lower)  for regex in virus_re) :
			addDoc = True
			
		if addDoc:
			insertrecords.append(record)
			
	#print("emptyAbstractCount=",emptyAbstractCount)
	#print("hasPDFParse=",hasPDFParse)
	#print("hasPMCParse=",hasPMCParse)
			
	#assert False

	mycursor.executemany(updatesql, updaterecords)
	print("%d documents updated" % len(updaterecords))

	print("%d documents found to possibly added" % len(insertrecords))

	if args.addcount:
		selected = random.sample(insertrecords,args.addcount)
		mycursor.executemany(insertsql, selected)
		print("Added %d documents" % len(selected))

	#insertsql = "INSERT INTO annotationoptions(name) VALUES(%s)"
	#annotation_options = [ ['SARS-CoV'],['MERS-CoV'],['SARS-CoV-2'] ]
	#mycursor.executemany(insertsql, annotation_options)
	#print("Added %d annotation options" % len(annotation_options))


	#insertsql = "INSERT INTO keywords(name) VALUES(%s)"
	#keywords = sum(virus_keywords.values(),[])
	#keywords = [ (k,) for k in keywords ]
	#mycursor.executemany(insertsql, keywords)
	#print("Added %d keywords options" % len(keywords))

	mydb.commit()
