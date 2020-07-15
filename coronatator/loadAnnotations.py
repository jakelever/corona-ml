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
	
	sql = "DELETE FROM annotations"
	print(sql)
	mycursor.execute(sql)
	
	sql = "DELETE FROM annotationpositions"
	print(sql)
	mycursor.execute(sql)
	
	
	sql = "DELETE FROM entities"
	print(sql)
	mycursor.execute(sql)
	
	sql = "DELETE FROM entitytypes"
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
	print()
		
	sql = "SELECT entitytype_id,name FROM entitytypes"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()
	entitytype_to_id = { (name,):entitytype_id for entitytype_id,name in myresult }
	print("Found %d existing entity types" % len(entitytype_to_id))
	
	sql = "SELECT entity_id,name,entitytype_id FROM entities"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()
	entity_to_id = { (name,entitytype_id):entity_id for entity_id,name,entitytype_id in myresult }
	print("Found %d existing entities" % len(entity_to_id))
	
	sql = "SELECT annotation_id,document_id,entity_id,is_automatic,is_positive FROM annotations"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()
	annotation_to_id = { (document_id,entity_id,is_automatic,is_positive):annotation_id for annotation_id,document_id,entity_id,is_automatic,is_positive in myresult }
	print("Found %d existing annotations" % len(annotation_to_id))
	
	
	sql = "SELECT annotationposition_id,annotation_id,in_title,start_pos,end_pos FROM annotationpositions"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()
	annotationposition_to_id = { (annotation_id,in_title,start_pos,end_pos):annotationposition_id for annotationposition_id,annotation_id,in_title,start_pos,end_pos in myresult }
	print("Found %d existing annotation positions" % len(annotationposition_to_id))
	
	print()
	
	
	print("Matching annotations to documents")
	for anno in annotations:
		cord_uid = anno['cord_uid']
		pubmed_id = anno['pubmed_id']
		entity_name = anno['entity_name']
		entity_type = anno['entity_type']

		if cord_uid in cord_to_document_id:
			document_id = cord_to_document_id[cord_uid]
		elif pubmed_id in pubmed_to_document_id:
			document_id = pubmed_to_document_id[pubmed_id]
		else:
			continue
			#raise RuntimeError("Couldn't find matching document for annotation with cord_uid=%s and pubmed_id=%s" % (cord_uid,pubmed_id))
		anno['document_id'] = document_id
		
	annotations = [ anno for anno in annotations if 'document_id' in anno ]
	
	
	
	
	
	def sortNewFromOldAndAddToDB(allRecords,existingMapping,insertSQL):
		assert isinstance(allRecords,list)
		assert isinstance(existingMapping,dict)
		
		for x in allRecords:
			assert isinstance(x, tuple)
	
		allRecords = set([ x for x in allRecords ])
		newRecords = sorted([ x for x in allRecords if not x in existingMapping ])
		index_offset = max(existingMapping.values())+1 if len(existingMapping) > 0 else 1
		
		newRecordsWithID = { x:(i+index_offset) for i,x in enumerate(newRecords) }
		existingMapping.update(newRecordsWithID)
		recordsForDB = [ [index] + list(x) for x,index in newRecordsWithID.items() ]
		
		print(insertSQL)
		print("Adding %d rows" % len(recordsForDB))
		print()
		for chunk in chunks(recordsForDB, 500):
			mycursor.executemany(insertSQL, chunk)
			
			
			
	insert_entity_type_sql = "INSERT INTO entitytypes(entitytype_id,name) VALUES(%s,%s)"
	entitytype_records = [ (anno['entity_type'],) for anno in annotations ]
	sortNewFromOldAndAddToDB(entitytype_records, entitytype_to_id, insert_entity_type_sql)
				
	print(entitytype_to_id)
				
	insert_entity_sql = "INSERT INTO entities(entity_id,name,entitytype_id,external_id) VALUES(%s,%s,%s,%s)"
	entity_records = []
	for anno in annotations:
		entity_name = anno['entity_name']
		entity_type = anno['entity_type']
		external_id = anno['external_id'] if 'external_id' in anno else None
		entitytype_id = entitytype_to_id[(entity_type,)]
		entity_records.append((entity_name,entitytype_id,external_id))
	sortNewFromOldAndAddToDB(entity_records, entity_to_id, insert_entity_sql)
		
	
			
	insert_annotation_sql = "INSERT INTO annotations(annotation_id,document_id,entity_id,is_automatic,is_positive) VALUES(%s,%s,%s,%s,%s)"
	anno_records = []
	for anno in annotations:
		document_id = anno['document_id']	
		entity_name = anno['entity_name']
		entity_type = anno['entity_type']
		entitytype_id = entitytype_to_id[(entity_type,)]
		external_id = anno['external_id'] if 'external_id' in anno else None
		entity_id = entity_to_id[(entity_name,entitytype_id,external_id)]
		is_automatic = (args.type == 'auto')
		is_positive = anno['is_positive'] if ('is_positive' in anno) else True
				
		anno_record = (document_id,entity_id,is_automatic,is_positive)
		anno_records.append(anno_record)
	sortNewFromOldAndAddToDB(anno_records, annotation_to_id, insert_annotation_sql)
	
	
	
	position_records = []
	insert_annotationposition_sql = "INSERT INTO annotationpositions(annotationposition_id,annotation_id,in_title,start_pos,end_pos) VALUES(%s,%s,%s,%s,%s)"
	annotationsWithPositions = [ anno for anno in annotations if all( k in anno for k in ['section','start_pos','end_pos'] ) ]
	for anno in annotationsWithPositions:
		document_id = anno['document_id']
		
		entity_name = anno['entity_name']
		entity_type = anno['entity_type']
		entitytype_id = entitytype_to_id[(entity_type,)]
		external_id = anno['external_id'] if 'external_id' in anno else None
		entity_id = entity_to_id[(entity_name,entitytype_id,external_id)]
		is_automatic = (args.type == 'auto')
		is_positive = anno['is_positive'] if ('is_positive' in anno) else True
				
		anno_record = (document_id,entity_id,is_automatic,is_positive)
		
		annotation_id = annotation_to_id[anno_record]
		
		in_title = (anno['section'] == 'title')
		start_pos = anno['start_pos']
		end_pos = anno['end_pos']
		
		position_record = (annotation_id,in_title,start_pos,end_pos)
		position_records.append(position_record)
		
	sortNewFromOldAndAddToDB(position_records, annotationposition_to_id, insert_annotationposition_sql)
			
	
	
	mydb.commit()
	