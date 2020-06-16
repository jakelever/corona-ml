import mysql.connector
from collections import OrderedDict
import csv

def chunks(lst, n):
	"""Yield successive n-sized chunks from lst."""
	for i in range(0, len(lst), n):
		yield lst[i:i + n]

with open('local.json') as f:
	database = json.load(f)

mydb = mysql.connector.connect(
	host=database['host'],
	user=database['user'],
	passwd=database['passwd'],
	database=database['database']
)

mycursor = mydb.cursor()

mycursor.execute("DROP TABLE IF EXISTS documents")
mycursor.execute("DROP TABLE IF EXISTS autoannotations")
mycursor.execute("DROP TABLE IF EXISTS manualannotations")

columns = OrderedDict()
columns['document_id'] = 'INT NOT NULL AUTO_INCREMENT'
columns['pmid'] = 'INT'
columns['pubdate'] = 'DATE'
columns['title'] = 'TEXT'
columns['abstract'] = 'TEXT'

fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
sql = "CREATE TABLE documents (%s)" % fields
print(sql)
mycursor.execute(sql)


columns = OrderedDict()
columns['autoannotation_id'] = 'INT NOT NULL AUTO_INCREMENT'
columns['document_id'] = 'INT'
columns['annotation'] = 'VARCHAR(255)'

fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
sql = "CREATE TABLE autoannotations (%s)" % fields
print(sql)
mycursor.execute(sql)


columns = OrderedDict()
columns['manualannotation_id'] = 'INT NOT NULL AUTO_INCREMENT'
columns['document_id'] = 'INT'
columns['annotation'] = 'VARCHAR(255)'

fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
sql = "CREATE TABLE manualannotations (%s)" % fields
print(sql)
mycursor.execute(sql)

covidKeywords = {'covid-19','covid 19','sars-cov-2','sars cov 2','sars-cov 2','sars cov-2','sars-cov2','sars cov2','sarscov2'}

records = []
with open('metadata.csv', newline='',encoding="utf-8") as csvfile:
	csvreader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
	for i,row in enumerate(csvreader):
		#print(row)
		#assert False
		combined_text = "%s\n%s" % (row['title'],row['abstract'])
		combined_text_lower = combined_text.lower()
		
		if not any(keyword in combined_text_lower for keyword in covidKeywords):
			continue
			
		title = row['title']
		abstract = row['abstract']
		pmid = row['pubmed_id']
		record = (pmid,title,abstract)
		records.append(record)
		#title = row['title']
		#break
		
print(len(records))
		
sql = "INSERT INTO documents (pmid,title,abstract) VALUES (%s,%s,%s)"

for chunk in chunks(records, 500):
	mycursor.executemany(sql, chunk)

mydb.commit()
