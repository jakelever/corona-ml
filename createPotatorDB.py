import mysql.connector
from collections import OrderedDict
import csv
import json

def chunks(lst, n):
	"""Yield successive n-sized chunks from lst."""
	for i in range(0, len(lst), n):
		yield lst[i:i + n]

with open('local-potator.json') as f:
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

fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
sql = "CREATE TABLE documents (%s)" % fields
print(sql)
mycursor.execute(sql)

columns = OrderedDict()
columns['annotation_id'] = 'INT NOT NULL AUTO_INCREMENT'
columns['document_id'] = 'INT'
columns['annotationoption_id'] = 'INT'

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
