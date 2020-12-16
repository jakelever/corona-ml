import mysql.connector
import json
import argparse
from collections import defaultdict

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Dump out annotations for use with pipeline')
	parser.add_argument('--db',required=True,type=str,help='JSON with database settings')
	parser.add_argument('--outData',required=True,type=str,help='Annotations in JSON format')
	args = parser.parse_args()
	
	with open(args.db) as f:
		database = json.load(f)

	mydb = mysql.connector.connect(
		host=database['host'],
		user=database['user'],
		passwd=database['passwd'],
		database=database['database']
	)
	
	sql = "SELECT d.cord_uid as cord_uid, d.pubmed_id as pubmed_id, d.phase as phase, ao.name as name FROM documents d, annotations a, annotationoptions ao WHERE d.document_id = a.document_id AND a.annotationoption_id = ao.annotationoption_id"
	
	mycursor = mydb.cursor()
	mycursor.execute(sql)
	myresult = mycursor.fetchall()

	annotations_by_cord = defaultdict(set)
	annotations_by_pubmed_id = defaultdict(set)
	for cord_uid,pubmed_id,phase,annotation in myresult:
		if cord_uid:
			annotations_by_cord[cord_uid].add(annotation)
			annotations_by_cord[cord_uid].add(phase)
		if pubmed_id:
			annotations_by_pubmed_id[str(pubmed_id)].add(annotation)
			annotations_by_pubmed_id[str(pubmed_id)].add(phase)
			
	annotations_by_cord = { cord_uid:sorted(annos) for cord_uid,annos in annotations_by_cord.items() }
	annotations_by_pubmed_id = { pubmed_id:sorted(annos) for pubmed_id,annos in annotations_by_pubmed_id.items() }
			
	output = {'annotations_by_cord':annotations_by_cord, 'annotations_by_pubmed_id':annotations_by_pubmed_id}
	
	with open(args.outData,'w',encoding='utf8') as f:
		json.dump(output,f,indent=2,sort_keys=True)
	
