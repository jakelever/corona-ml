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
	
	sql = "SELECT document_id,pubmed_id,cord_uid,doi,url FROM documents"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()

	pubmed_to_document_id = {str(pubmed_id):document_id for document_id,pubmed_id,cord_ui,doi,url in myresult if pubmed_id }
	cord_to_document_id = {cord_ui:document_id for document_id,pubmed_id,cord_ui,doi,url in myresult if cord_ui }
	doi_to_document_id = {doi:document_id for document_id,pubmed_id,cord_ui,doi,url in myresult if doi }
	url_to_document_id = {url:document_id for document_id,pubmed_id,cord_ui,doi,url in myresult if url }

	print("Found %d Pubmed mappings" % len(pubmed_to_document_id))
	print("Found %d CORD mappings" % len(cord_to_document_id))
	print("Found %d DOI mappings" % len(doi_to_document_id))
	print("Found %d URL mappings" % len(url_to_document_id))
	print()
	
	print("Matching annotations to documents")
	for anno in annotations:
		cord_uid = anno['cord_uid']
		pubmed_id = anno['pubmed_id']
		doi = anno['doi']
		url = anno['url']
		
		entity_name = anno['entity_name']
		entity_type = anno['entity_type']
		
		assert 'external_id' in anno and anno['external_id'], "Found empty external_id for annotation: %s" % str(anno)

		if cord_uid and cord_uid in cord_to_document_id:
			document_id = cord_to_document_id[cord_uid]
		elif pubmed_id and pubmed_id in pubmed_to_document_id:
			document_id = pubmed_to_document_id[pubmed_id]
		elif doi and doi in doi_to_document_id:
			document_id = doi_to_document_id[doi]
		elif url and url in url_to_document_id:
			document_id = url_to_document_id[url]
		else:
			continue
			#raise RuntimeError("Couldn't find matching document for annotation with cord_uid=%s and pubmed_id=%s" % (cord_uid,pubmed_id))
		anno['document_id'] = document_id
		
	annotations = [ anno for anno in annotations if 'document_id' in anno ]
			
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
		
	
	insert_annotation_sql = "INSERT INTO annotations(annotation_id,document_id,entity_id,is_automatic,is_positive) VALUES(%s,%s,%s,%s,%s)"
	annotation_to_id, anno_records = {}, []
	for anno in annotations:
		document_id = anno['document_id']	
		entity_name = anno['entity_name']
		entity_type = anno['entity_type']
		entitytype_id = entitytype_to_id[entity_type]
		external_id = anno['external_id'] if 'external_id' in anno else None
		entity_id = entity_to_id[(entity_name,entitytype_id,external_id)]
		is_automatic = (args.type == 'auto')
		is_positive = anno['is_positive'] if ('is_positive' in anno) else True
				
		anno_record = (document_id,entity_id,is_automatic,is_positive)
		
		if not anno_record in annotation_to_id:
			annotation_id = len(annotation_to_id) + 1
			annotation_to_id[anno_record] = annotation_id
			
			anno_records.append((annotation_id,document_id,entity_id,is_automatic,is_positive))
	
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
		is_automatic = (args.type == 'auto')
		is_positive = anno['is_positive'] if ('is_positive' in anno) else True
				
		anno_record = (document_id,entity_id,is_automatic,is_positive)
		
		annotation_id = annotation_to_id[anno_record]
		
		in_title = (anno['section'] == 'title')
		start_pos = anno['start_pos']
		end_pos = anno['end_pos']
		
		position_record = (i+1,annotation_id,in_title,start_pos,end_pos)
		position_records.append(position_record)
		
	for chunk in chunks(position_records, 500):
		mycursor.executemany(insert_annotationspan_sql, chunk)
			
	
	
	mydb.commit()
	