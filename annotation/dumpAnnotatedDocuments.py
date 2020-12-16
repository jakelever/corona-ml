import mysql.connector
import json
import argparse
from collections import defaultdict

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Dump out documents with annotations')
	parser.add_argument('--db',required=True,type=str,help='JSON with database settings')
	parser.add_argument('--outData',required=True,type=str,help='Documents with annotations in JSON format')
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
	
	sql = "SELECT document_id, title, abstract, journal, cord_uid, pubmed_id, phase FROM documents"
	
	documents = {}
	
	mycursor.execute(sql)
	myresult = mycursor.fetchall()
	for document_id, title, abstract, journal, cord_uid, pubmed_id, phase in myresult:
		document = { 'title': title, 'abstract':abstract, 'journal':journal, 'cord_uid':cord_uid, 'pubmed_id':pubmed_id, 'annotations':[phase] }
		documents[document_id] = document
	
	
	sql = "SELECT d.document_id as document_id, ao.name as name FROM documents d, annotations a, annotationoptions ao WHERE d.document_id = a.document_id AND a.annotationoption_id = ao.annotationoption_id"
	
	mycursor.execute(sql)
	myresult = mycursor.fetchall()

	for document_id,annotation in myresult:
		documents[document_id]['annotations'].append(annotation)
		
	for document_id,document in documents.items():
		document['annotations'] = sorted(set(document['annotations']))
			
	output = list(documents.values())	
	
	with open(args.outData,'w',encoding='utf8') as f:
		json.dump(output,f,indent=2,sort_keys=True)
	