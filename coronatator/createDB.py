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
	parser = argparse.ArgumentParser('Create tables in database (and will remove old data!)')
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

	mycursor.execute("DROP TABLE IF EXISTS documents")
	mycursor.execute("DROP TABLE IF EXISTS annotations")
	mycursor.execute("DROP TABLE IF EXISTS entities")
	mycursor.execute("DROP TABLE IF EXISTS entitytypes")

	columns = OrderedDict()
	columns['document_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['pubmed_id'] = 'INT NULL'
	columns['cord_uid'] = 'VARCHAR(255) NULL'
	columns['doi'] = 'VARCHAR(255) NULL'
	columns['publish_year'] = 'INT'
	columns['publish_month'] = 'INT'
	columns['publish_day'] = 'INT'
	columns['title'] = 'TEXT'
	columns['abstract'] = 'TEXT'
	columns['journal'] = 'TEXT'
	columns['url'] = 'VARCHAR(255)'
	columns['mesh'] = 'TEXT NULL'
	columns['has_mesh'] = 'BOOLEAN'
	columns['pub_type'] = 'VARCHAR(255)'
	columns['chemicals'] = 'TEXT NULL'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	sql = "CREATE TABLE documents (%s)" % fields
	print(sql)
	mycursor.execute(sql)

	columns = OrderedDict()
	columns['annotation_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['document_id'] = 'INT'
	columns['entity_id'] = 'INT'
	columns['is_automatic'] = 'BOOLEAN'
	columns['is_positive'] = 'BOOLEAN'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	fields += ", INDEX(document_id)"
	fields += ", INDEX(entity_id)"
	sql = "CREATE TABLE annotations (%s)" % fields
	print(sql)
	mycursor.execute(sql)

	columns = OrderedDict()
	columns['entity_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['entity_name'] = 'VARCHAR(255)'
	columns['external_id'] = 'VARCHAR(255)'
	columns['entitytype_id'] = 'INT DEFAULT 1'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	fields += ", INDEX(entity_name)"
	sql = "CREATE TABLE entities (%s)" % fields
	print(sql)
	mycursor.execute(sql)

	columns = OrderedDict()
	columns['entitytype_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['entitytype_name'] = 'VARCHAR(255)'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	fields += ", INDEX(entitytype_name)"
	sql = "CREATE TABLE entitytypes (%s)" % fields
	print(sql)
	mycursor.execute(sql)

	sql = "INSERT INTO entitytypes(entitytype_id,entitytype_name) VALUES (1,'undefined')"
	print(sql)
	mycursor.execute(sql)

	mydb.commit()
