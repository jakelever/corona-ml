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
	
	engine = "MyISAM"
		
	mycursor = mydb.cursor()

	mycursor.execute("DROP TABLE IF EXISTS documents")
	mycursor.execute("DROP TABLE IF EXISTS annotations")
	mycursor.execute("DROP TABLE IF EXISTS annotationpositions")
	mycursor.execute("DROP TABLE IF EXISTS annotationspans")
	mycursor.execute("DROP TABLE IF EXISTS entities")
	mycursor.execute("DROP TABLE IF EXISTS entitytypes")
	mycursor.execute("DROP TABLE IF EXISTS coordinates")

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
	columns['altmetric_id'] = 'INT DEFAULT -1'
	columns['altmetric_score'] = 'INT DEFAULT 0'
	columns['altmetric_score_1day'] = 'INT DEFAULT 0'
	columns['altmetric_score_1week'] = 'INT DEFAULT 0'
	columns['altmetric_openaccess'] = 'BOOLEAN DEFAULT FALSE'
	columns['altmetric_badgetype'] = 'VARCHAR(64) NULL'
	columns['altmetric_lastupdated'] = 'DATETIME'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	fields += ", INDEX(altmetric_score_1day)"
	sql = "CREATE TABLE documents (%s) ENGINE=%s" % (fields,engine)
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
	sql = "CREATE TABLE annotations (%s) ENGINE=%s" % (fields,engine)
	print(sql)
	mycursor.execute(sql)

	columns = OrderedDict()
	columns['entity_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['name'] = 'VARCHAR(255)'
	columns['external_id'] = 'VARCHAR(255)'
	columns['entitytype_id'] = 'INT DEFAULT 1'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	fields += ", INDEX(name)"
	sql = "CREATE TABLE entities (%s) ENGINE=%s" % (fields,engine)
	print(sql)
	mycursor.execute(sql)

	columns = OrderedDict()
	columns['entitytype_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['name'] = 'VARCHAR(255)'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	fields += ", INDEX(name)"
	sql = "CREATE TABLE entitytypes (%s) ENGINE=%s" % (fields,engine)
	print(sql)
	mycursor.execute(sql)
	
	columns = OrderedDict()
	columns['entity_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['longitude'] = 'FLOAT'
	columns['latitude'] = 'FLOAT'
	
	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	sql = "CREATE TABLE coordinates (%s) ENGINE=%s" % (fields,engine)
	print(sql)
	mycursor.execute(sql)

	#sql = "INSERT INTO entitytypes(entitytype_id,name) VALUES (1,'undefined')"
	#print(sql)
	#mycursor.execute(sql)
	
	columns = OrderedDict()
	columns['annotationspan_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['annotation_id'] = 'INT'
	columns['in_title'] = 'BOOLEAN'
	columns['start_pos'] = 'INT'
	columns['end_pos'] = 'INT'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	fields += ", INDEX(annotation_id)"
	sql = "CREATE TABLE annotationspans (%s) ENGINE=%s" % (fields,engine)
	print(sql)
	mycursor.execute(sql)

	mydb.commit()
