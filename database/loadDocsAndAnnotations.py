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
			
	doc_columns = ['document_id', 'pubmed_id', 'cord_uid', 'doi', 'pmcid', 'publish_year', 'publish_month', 'publish_day', 'publish_timestamp', 'title', 'abstract', 'journal', 'url', 'is_preprint']
	
	dbfields = ",".join(doc_columns)
	dbvalues = ",".join('%s' for _ in doc_columns)
	insertsql = "INSERT INTO documents (%s) VALUES (%s)" % (dbfields,dbvalues)
	print(insertsql)

	insertrecords = []
	for i,doc in enumerate(documents):
		doc['document_id'] = i+1
	
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
		
		record = [ doc[c] for c in doc_columns ]
		
		insertrecords.append(record)
		
	for chunk in chunks(insertrecords, 100):
		mycursor.executemany(insertsql, chunk)
		
	mydb.commit()
	print("Added %d documents" % len(insertrecords))
	
	
	
	
	
	
	annotations = []
	for d in documents:
		if not any(entity['type'] == 'Virus' for entity in d['entities']):
			continue
			
		cord_uid = d['cord_uid']
		pubmed_id = d['pubmed_id']
		doi = d['doi']
		url = d['url']
		
		assert cord_uid or pubmed_id or doi or url
		
		for category in d['categories']:
			aa = { 'document_id':d['document_id'], 'cord_uid': cord_uid, 'pubmed_id':pubmed_id, 'doi':doi, 'url':url, 'entity_type':'category', 'entity_name':category, 'external_id':'category_%s' % category, 'is_positive':True }
			annotations.append(aa)
			
		for entity in d['entities']:
			aa = { 'document_id':d['document_id'], 'cord_uid': cord_uid, 'pubmed_id':pubmed_id, 'doi':doi, 'url':url, 'entity_type':entity['type'], 'entity_name':entity['normalized'], 'external_id':entity['id'], 'start_pos':entity['start'], 'end_pos':entity['end'], 'section':entity['section'] }
			annotations.append(aa)
	
	
	insert_entity_type_sql = "INSERT INTO entitytypes(entitytype_id,name) VALUES(%s,%s)"
	entity_types = sorted(set( anno['entity_type'] for anno in annotations ))
	entitytype_to_id, entitytype_records = {}, []
	for i,anno in enumerate(annotations):
		entity_type = anno['entity_type']
		if not entity_type in entitytype_to_id:
			entitytype_id = len(entitytype_to_id) + 1
			entitytype_to_id[entity_type] = entitytype_id
			
			entitytype_records.append( (entitytype_id,entity_type) )
	
	mycursor.executemany(insert_entity_type_sql, entitytype_records)
	print("Added %d entity types" % len(entitytype_records))
				
	insert_entity_sql = "INSERT INTO entities(entity_id,name,entitytype_id,external_id) VALUES(%s,%s,%s,%s)"
	entity_to_id, entity_records = {}, []
	for anno in annotations:
		entity_name = anno['entity_name']
		entity_type = anno['entity_type']
		external_id = anno['external_id'] if 'external_id' in anno else None
		entitytype_id = entitytype_to_id[entity_type]
		if not (entity_name,entitytype_id,external_id) in entity_to_id:
			entity_id = len(entity_to_id) + 1
			entity_to_id[(entity_name,entitytype_id,external_id)] = entity_id
			
			entity_records.append((entity_id,entity_name,entitytype_id,external_id))
	
	for chunk in chunks(entity_records, 500):
		mycursor.executemany(insert_entity_sql, chunk)
		
	
	insert_annotation_sql = "INSERT INTO annotations(annotation_id,document_id,entity_id) VALUES(%s,%s,%s)"
	annotation_to_id, anno_records = {}, []
	for anno in annotations:
		document_id = anno['document_id']	
		entity_name = anno['entity_name']
		entity_type = anno['entity_type']
		entitytype_id = entitytype_to_id[entity_type]
		external_id = anno['external_id'] if 'external_id' in anno else None
		entity_id = entity_to_id[(entity_name,entitytype_id,external_id)]
				
		anno_record = (document_id,entity_id)
		
		if not anno_record in annotation_to_id:
			annotation_id = len(annotation_to_id) + 1
			annotation_to_id[anno_record] = annotation_id
			
			anno_records.append((annotation_id,document_id,entity_id))
	
	for chunk in chunks(anno_records, 500):
		mycursor.executemany(insert_annotation_sql, chunk)
	
	
	position_records = []
	insert_annotationspan_sql = "INSERT INTO annotationspans(annotationspan_id,annotation_id,in_title,start_pos,end_pos) VALUES(%s,%s,%s,%s,%s)"
	annotationsWithPositions = [ anno for anno in annotations if all( k in anno for k in ['section','start_pos','end_pos'] ) ]
	for i,anno in enumerate(annotationsWithPositions):
		document_id = anno['document_id']
		
		entity_name = anno['entity_name']
		entity_type = anno['entity_type']
		entitytype_id = entitytype_to_id[entity_type]
		external_id = anno['external_id'] if 'external_id' in anno else None
		entity_id = entity_to_id[(entity_name,entitytype_id,external_id)]
				
		anno_record = (document_id,entity_id)
		
		annotation_id = annotation_to_id[anno_record]
		
		in_title = (anno['section'] == 'title')
		start_pos = anno['start_pos']
		end_pos = anno['end_pos']
		
		position_record = (i+1,annotation_id,in_title,start_pos,end_pos)
		position_records.append(position_record)
		
	for chunk in chunks(position_records, 500):
		mycursor.executemany(insert_annotationspan_sql, chunk)