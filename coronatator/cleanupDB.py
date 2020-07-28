import argparse
import mysql.connector
from collections import Counter
import csv
import json
		
if __name__ == '__main__':
	parser = argparse.ArgumentParser('Run some cleanup routines to remove dead annotations')
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
	
	sql = "DELETE FROM annotations WHERE document_id NOT IN (SELECT document_id FROM documents)"
	print(sql)
	mycursor.execute(sql)
	print("Deleted %d annotations" % mycursor.rowcount)
	
	sql = "DELETE FROM annotationpositions WHERE annotation_id NOT IN (SELECT annotation_id FROM annotations)"
	print(sql)
	mycursor.execute(sql)
	print("Deleted %d annotationpositions" % mycursor.rowcount)
	
	sql = "DELETE FROM entities WHERE entity_id NOT IN (SELECT entity_id FROM annotations)"
	print(sql)
	mycursor.execute(sql)
	print("Deleted %d entities" % mycursor.rowcount)
	
	sql = "DELETE FROM entitytypes WHERE entitytype_id NOT IN (SELECT entitytype_id FROM entities)"
	print(sql)
	mycursor.execute(sql)
	print("Deleted %d entitytypes" % mycursor.rowcount)
	
	sql = "DELETE FROM coordinates WHERE entity_id NOT IN (SELECT entity_id FROM annotations)"
	print(sql)
	mycursor.execute(sql)
	print("Deleted %d coordinates" % mycursor.rowcount)
	
	mydb.commit()
	