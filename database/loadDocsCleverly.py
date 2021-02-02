import mysql.connector
from collections import OrderedDict
import csv
import json
import argparse
from datetime import datetime, date
import calendar

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
	columns['publish_timestamp'] = 'INT'
	columns['title'] = 'TEXT'
	columns['abstract'] = 'TEXT'
	columns['journal'] = 'TEXT'
	columns['url'] = 'VARCHAR(255)'
	columns['is_preprint'] = 'BOOL'

	dbfields = ",".join(columns.keys())
	dbvalues = ",".join('%s' for _ in columns.keys())
	insertsql = "INSERT INTO documents (%s) VALUES (%s)" % (dbfields,dbvalues)
	print(insertsql)

	insertrecords = []
	for doc in documents:
		if not doc['pubmed_id']:
			doc['pubmed_id'] = None
		if not doc['cord_uid']:
			doc['cord_uid'] = None
		if not doc['pmcid']:
			doc['pmcid'] = None
		
		publish_year = doc['publish_year'] if doc['publish_year'] else 2020
		publish_month = doc['publish_month'] if doc['publish_month'] else 1
		publish_day = doc['publish_day'] if doc['publish_day'] else 1
		
		publish_date = datetime(publish_year, publish_month, publish_day, 12, 0, 0)
		doc['publish_timestamp'] = calendar.timegm(publish_date.timetuple())
		
		record = [ doc[c] for c in columns.keys() ]
		
		insertrecords.append(record)
		
	for chunk in chunks(insertrecords, 100):
		mycursor.executemany(insertsql, chunk)
		
	mydb.commit()
	print("Added %d documents" % len(insertrecords))