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
	parser.add_argument('--json',required=True,type=str,help='JSON file with altmetric data')
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
	
	mycursor.execute("DROP TABLE IF EXISTS tmp_altmetric")
	columns = OrderedDict()
	columns['document_id'] = 'INT NOT NULL AUTO_INCREMENT'
	columns['altmetric_id'] = 'INT DEFAULT -1'
	columns['altmetric_score'] = 'INT DEFAULT -1'
	columns['altmetric_score_1day'] = 'INT DEFAULT -1'
	columns['altmetric_score_1week'] = 'INT DEFAULT -1'
	columns['altmetric_openaccess'] = 'BOOLEAN DEFAULT FALSE'
	columns['altmetric_badgetype'] = 'VARCHAR(64) NULL'

	fields = ", ".join("%s %s" % (n,t) for n,t in columns.items())
	fields += ", PRIMARY KEY(%s)" % list(columns.keys())[0]
	sql = "CREATE TABLE tmp_altmetric (%s)" % fields
	print(sql)
	mycursor.execute(sql)
	
	
	#update_altmetric_sql = "UPDATE documents SET altmetric_id=%s, altmetric_score=%s, altmetric_score_1day=%s, altmetric_score_1week=%s, altmetric_openaccess=%s, altmetric_badgetype=%s, altmetric_lastupdated=NOW() WHERE document_id=%s"
	insert_altmetric_sql = "INSERT INTO tmp_altmetric(altmetric_id,altmetric_score,altmetric_score_1day,altmetric_score_1week,altmetric_openaccess,altmetric_badgetype,document_id) VALUES(%s,%s,%s,%s,%s,%s,%s)"
		
	#updatesByDoc = {}
	updates = []
	for record in records:
		if record['altmetric']['response'] == False:
			continue
			
		cord_uid = record['cord_uid']
		pubmed_id = record['pubmed_id']

		if cord_uid in cord_to_document_id:
			document_id = cord_to_document_id[cord_uid]
		elif pubmed_id in pubmed_to_document_id:
			document_id = pubmed_to_document_id[pubmed_id]
		else:
			continue
			#raise RuntimeError("Couldn't find matching document for annotation with cord_uid=%s and pubmed_id=%s" % (cord_uid,pubmed_id))
			
		altdata = record['altmetric']
		
		badgeMatch = re.match(r"^https://badges.altmetric.com/\?size=\d+&score=\d+&types=(?P<badgetype>\w+)$", altdata['images']['large'])
		assert badgeMatch, "Didn't manage to extract info from badge URL: %s" % altdata['images']['large']
		
		altmetric_id = altdata['altmetric_id']
		altmetric_score = altdata['score']
		altmetric_score_1day = altdata['history']['1d']
		altmetric_score_1week = altdata['history']['1d']
		altmetric_openaccess = altdata['is_oa']
		altmetric_badgetype = badgeMatch.groupdict()['badgetype']
		
		update = [ altmetric_id, altmetric_score, altmetric_score_1day, altmetric_score_1week, altmetric_openaccess, altmetric_badgetype, document_id ]
		updates.append(update)
		#updatesByDoc[document_id] = update
		#print(document_id)
		
		#break
		
	#updates = sorted(updatesByDoc.values())
		
	chunk_size = 1000
	for i,chunk in enumerate(chunks(updates, chunk_size)):
		num_complete = i*chunk_size
		print("  %.1f%% (%d/%d)" % (100*num_complete/len(updates),num_complete,len(updates)))
		#mycursor.executemany(update_altmetric_sql, chunk)
		mycursor.executemany(insert_altmetric_sql, chunk)
		
	merge_sql = """
	UPDATE documents d, tmp_altmetric ta
	SET d.altmetric_id = ta.altmetric_id, 
		d.altmetric_score = ta.altmetric_score, 
		d.altmetric_score_1day = ta.altmetric_score_1day, 
		d.altmetric_score_1week = ta.altmetric_score_1week, 
		d.altmetric_openaccess = ta.altmetric_openaccess, 
		d.altmetric_badgetype = ta.altmetric_badgetype, 
		d.altmetric_lastupdated = NOW()
	WHERE d.document_id = ta.document_id
	"""
	
	mycursor.execute(merge_sql)
	
	mycursor.execute("DROP TABLE IF EXISTS tmp_altmetric")
		
	mydb.commit()
	print("Updated %d documents with Altmetric data" % len(updates))
