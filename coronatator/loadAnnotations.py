import argparse
import mysql.connector
from collections import Counter
import csv
import json
		
def chunks(lst, n):
	"""Yield successive n-sized chunks from lst."""
	for i in range(0, len(lst), n):
		yield lst[i:i + n]
		
if __name__ == '__main__':
	parser = argparse.ArgumentParser('Load annotations into database')
	parser.add_argument('--type',required=True,type=str,help='Type of annotations (auto/manual)')
	parser.add_argument('--db',required=True,type=str,help='JSON with database settings')
	parser.add_argument('--json',required=True,type=str,help='JSON file with annotations')
	args = parser.parse_args()
	
	with open(args.db) as f:
		database = json.load(f)

	mydb = mysql.connector.connect(
	  host=database['host'],
	  user=database['user'],
	  passwd=database['passwd'],
	  database=database['database']
	)
		
	#assert args.type in ['auto','manual']
	assert args.type == 'auto'
	
	with open(args.json) as f:
		annotations = json.load(f)

	mycursor = mydb.cursor()
	
	sql = "DELETE FROM annotations WHERE is_automatic = TRUE"
	print(sql)
	mycursor.execute(sql)

	sql = "SELECT document_id,pubmed_id,cord_uid FROM documents"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()

	pubmed_to_document_id = {}
	cord_to_document_id = {}

	pubmed_to_document_id = {str(pubmed_id):document_id for document_id,pubmed_id,cord_ui in myresult if pubmed_id }
	cord_to_document_id = {cord_ui:document_id for document_id,pubmed_id,cord_ui in myresult if cord_ui }

	print("Found %d Pubmed mappings" % len(pubmed_to_document_id))
	print("Found %d CORD mappings" % len(cord_to_document_id))
	
	sql = "SELECT document_id,entity_id,is_automatic,is_positive FROM annotations"
	mycursor.execute(sql)
	myresult = mycursor.fetchall()	
	existing_annotations = set([ (document_id,entity_id,is_automatic,is_positive) for document_id,entity_id,is_automatic,is_positive in myresult ])
	
	print("Found %d existing annotations" % len(existing_annotations))

	#for record in myresult:
	#	document_id,pubmed_id,cord_ui = record
	#	assert pubmed_id or cord_ui
		#break
		
	sql = "SELECT entity_id,entity_name,entitytype_id FROM entities"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()
	entity_name_to_id = { entity_name:entity_id for entity_id,entity_name,entitytype_id in myresult }

	sql = "SELECT entitytype_id,entitytype_name FROM entitytypes"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()
	entitytype_name_to_id = { entitytype_name:entitytype_id for entitytype_id,entitytype_name in myresult }
	
	addition_counts = Counter()
	
	insert_entity_type_sql = "INSERT INTO entitytypes(entitytype_id,entitytype_name) VALUES(%s,%s)"
	print(insert_entity_type_sql)
	entitytype_records = []
	for anno in annotations:
		entity_type = anno['entity_type']
		
		if not entity_type in entitytype_name_to_id:
			entitytype_id = (max(entitytype_name_to_id.values()) + 1) if len(entitytype_name_to_id) > 0 else 1
			entitytype_record = [entitytype_id,entity_type]
			#mycursor.execute(insert_entity_type_sql, entitytype_record)
			entitytype_records.append( entitytype_record )
			
			#entitytype_id = mycursor.lastrowid
			entitytype_name_to_id[entity_type] = entitytype_id
			addition_counts['entitytype'] += 1
			
	for chunk in chunks(entitytype_records, 500):
		mycursor.executemany(insert_entity_type_sql, chunk)
			
	insert_entity_sql = "INSERT INTO entities(entity_name,entitytype_id,external_id) VALUES(%s,%s,%s)"
	print(insert_entity_sql)
	
	entity_records = []
	for anno in annotations:
		entity_name = anno['entity_name']
		entity_type = anno['entity_type']
		external_id = anno['external_id'] if 'external_id' in anno else None
		if not entity_name in entity_name_to_id:
			entitytype_id = entitytype_name_to_id[entity_type]
			entity_id = (max(entity_name_to_id.values()) + 1) if len(entity_name_to_id) > 0 else 1
			entity_record = [entity_name,entitytype_id,external_id]
			
			entity_records.append(entity_record)
			#mycursor.execute(insert_entity_sql, entity_record)
			#entity_id = mycursor.lastrowid
			entity_name_to_id[entity_name] = entity_id
			addition_counts['entity'] += 1
			
	for chunk in chunks(entity_records, 500):
		mycursor.executemany(insert_entity_sql, chunk)
			
	insert_annotation_sql = "INSERT INTO annotations(document_id,entity_id,is_automatic,is_positive) VALUES(%s,%s,%s,%s)"
	print(insert_annotation_sql)
	
	anno_records = []
	for anno in annotations:
		cord_uid = anno['cord_uid']
		pubmed_id = anno['pubmed_id']
		entity_name = anno['entity_name']
		entity_type = anno['entity_type']
		is_positive = anno['is_positive']

		if cord_uid in cord_to_document_id:
			document_id = cord_to_document_id[cord_uid]
		elif pubmed_id in pubmed_to_document_id:
			document_id = pubmed_to_document_id[pubmed_id]
		else:
			continue
			#raise RuntimeError("Couldn't find matching document for annotation with cord_uid=%s and pubmed_id=%s" % (cord_uid,pubmed_id))
		
		entity_id = entity_name_to_id[entity_name]
		is_automatic = (args.type == 'auto')
				
		record_data = [document_id,entity_id,is_automatic,is_positive]
		
		if not tuple(record_data) in existing_annotations:
			#mycursor.execute(insert_annotation_sql, record_data)
			anno_records.append(record_data)
			addition_counts['annotation'] += 1
			existing_annotations.add(tuple(record_data))
					
	for chunk in chunks(anno_records, 500):
		mycursor.executemany(insert_annotation_sql, chunk)
		
	mydb.commit()
	print("Added %d annotations" % addition_counts['annotation'])
	print("Added %d entities" % addition_counts['entity'])
	print("Added %d entity types" % addition_counts['entitytype'])
