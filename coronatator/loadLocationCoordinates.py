import argparse
import mysql.connector
from collections import Counter,OrderedDict
import csv
import json
import re
		
def chunks(lst, n):
	"""Yield successive n-sized chunks from lst."""
	for i in range(0, len(lst), n):
		yield lst[i:i + n]
		
if __name__ == '__main__':
	parser = argparse.ArgumentParser('Load annotations into database')
	parser.add_argument('--db',required=True,type=str,help='JSON with database settings')
	parser.add_argument('--json',required=True,type=str,help='JSON file with location data')
	args = parser.parse_args()
	
	with open(args.db) as f:
		database = json.load(f)

	mydb = mysql.connector.connect(
	  host=database['host'],
	  user=database['user'],
	  passwd=database['passwd'],
	  database=database['database']
	)
		
	with open(args.json) as f:
		records = json.load(f)

	mycursor = mydb.cursor()
	

	sql = "SELECT e.entity_id, e.external_id FROM entities e, entitytypes et WHERE e.entitytype_id = et.entitytype_id AND et.name = 'Location'"
	print(sql)
	mycursor.execute(sql)
	myresult = mycursor.fetchall()

	pubmed_to_document_id = {}
	cord_to_document_id = {}

	location_to_entity_id = {external_id:entity_id for entity_id,external_id in myresult }

	print("Found %d location mappings" % len(location_to_entity_id))
	
	mycursor.execute("DELETE FROM coordinates")
	
	
	with open(args.json) as f:
		locations = json.load(f)
	
	insert_coordinate_sql = "INSERT INTO coordinates (entity_id,longitude,latitude) VALUES(%s,%s,%s)"
	
	locationsWithIDs = [ (wikidataID,loc) for wikidataID,loc in locations.items() if wikidataID in location_to_entity_id ]
	
	loc_records = [ [ location_to_entity_id[wikidataID], loc['longitude'], loc['latitude'] ] for wikidataID,loc in locationsWithIDs ]
	#for wikidataID,loc in locations.items():
	#	print(loc)
		#name = loc['name']
	#	if name in location_to_entity_id:
	#		entity_id = location_to_entity_id[name]
	#		
	#		loc_record = 
	#		loc_records.append(loc_record)
			
	chunk_size = 1000
	for i,chunk in enumerate(chunks(loc_records, chunk_size)):
		mycursor.executemany(insert_coordinate_sql, chunk)
		
	mydb.commit()
	print("Added %d location coordinates" % len(loc_records))
