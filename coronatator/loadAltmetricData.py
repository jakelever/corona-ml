import argparse
import mysql.connector
from collections import Counter
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
	
	update_altmetric_sql = "UPDATE documents SET altmetric_id=%s, altmetric_score=%s, altmetric_score_1day=%s, altmetric_score_1week=%s, altmetric_openaccess=%s, altmetric_badgetype=%s, altmetric_lastupdated=NOW() WHERE document_id=%s"
		
	updates = []
	for record in records:
		cord_uid = record['identifiers']['cord_uid']
		pubmed_id = record['identifiers']['pubmed_id']

		if cord_uid in cord_to_document_id:
			document_id = cord_to_document_id[cord_uid]
		elif pubmed_id in pubmed_to_document_id:
			document_id = pubmed_to_document_id[pubmed_id]
		else:
			continue
			#raise RuntimeError("Couldn't find matching document for annotation with cord_uid=%s and pubmed_id=%s" % (cord_uid,pubmed_id))
		
		badgeMatch = re.match(r"^https://badges.altmetric.com/\?size=\d+&score=\d+&types=(?P<badgetype>\w+)$", record['images']['large'])
		assert badgeMatch, "Didn't manage to extract info from badge URL: %s" % record['images']['large']
		
		altmetric_id = record['altmetric_id']
		altmetric_score = record['score']
		altmetric_score_1day = record['history']['1d']
		altmetric_score_1week = record['history']['1d']
		altmetric_openaccess = record['is_oa']
		altmetric_badgetype = badgeMatch.groupdict()['badgetype']
		
		update = [ altmetric_id, altmetric_score, altmetric_score_1day, altmetric_score_1week, altmetric_openaccess, altmetric_badgetype, document_id ]
		updates.append(update)
		#print(document_id)
		
		#break
		
	for i,chunk in enumerate(chunks(updates, 500)):
		num_done = i*500
		print(num_done,len(updates))
		mycursor.executemany(update_altmetric_sql, chunk)
		
	mydb.commit()
	print("Updated %d documents with Altmetric data" % len(updates))
