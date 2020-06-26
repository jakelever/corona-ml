import csv

#cord_uid,sha,source_x,title,doi,pmcid,pubmed_id,license,abstract,publish_time,authors,journal,Microsoft Academic Paper ID,WHO #Covidence,has_pdf_parse,has_pmc_xml_parse,full_text_file,url

with open('metadata.csv',newline='',encoding="utf-8") as csvfile:
	csvreader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
	for i,row in enumerate(csvreader):
		row = {k:v.strip() for k,v in row.items() }
		if row['url'] == '':
			outK = ['source_x','doi','title']
			print("\t".join([row[k] for k in outK]))