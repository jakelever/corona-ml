import mysql.connector
from collections import OrderedDict
import csv
import json

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

	#mycursor.execute("DROP TABLE IF EXISTS documents")
	#mycursor.execute("DROP TABLE IF EXISTS annotations")
	#mycursor.execute("DROP TABLE IF EXISTS annotationoptions")
	#mycursor.execute("DROP TABLE IF EXISTS keywords")

	columns = OrderedDict()
	columns['document_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['pubmed_id'] = 'INT NULL'
	columns['cord_uid'] = 'VARCHAR(255) NULL'
	columns['title'] = 'TEXT'
	columns['abstract'] = 'TEXT'
	columns['publish_year'] = 'INT'
	columns['journal'] = 'TEXT'
	columns['url'] = 'VARCHAR(255)'
	columns['added'] = 'DATETIME NULL'
	columns['phase'] = 'VARCHAR(16)'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	sql = "CREATE TABLE documents (%s)" % fields
	print(sql)
	mycursor.execute(sql)

	columns = OrderedDict()
	columns['annotation_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['document_id'] = 'INT'
	columns['annotationoption_id'] = 'INT'
	columns['added'] = 'DATETIME NULL'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	sql = "CREATE TABLE annotations (%s)" % fields
	print(sql)
	mycursor.execute(sql)

	columns = OrderedDict()
	columns['annotationoption_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['name'] = 'VARCHAR(255)'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	sql = "CREATE TABLE annotationoptions (%s)" % fields
	print(sql)
	mycursor.execute(sql)

	columns = OrderedDict()
	columns['keyword_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['name'] = 'VARCHAR(255)'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	sql = "CREATE TABLE keywords (%s)" % fields
	print(sql)
	mycursor.execute(sql)
	
	columns = OrderedDict()
	columns['activequeue_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['document_id'] = 'INT'
	columns['task_id'] = 'INT'
	columns['dochash'] = 'VARCHAR(64)'
	columns['current_coverage'] = '0.5'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	sql = "CREATE TABLE activequeue (%s)" % fields
	print(sql)
	mycursor.execute(sql)
