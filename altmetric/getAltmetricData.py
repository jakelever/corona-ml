import argparse
import json
import requests
import urllib.parse
from collections import Counter
import time
import datetime
	
def nice_time(seconds):
	days = int(seconds) // (24*60*60)
	seconds -= days * (24*60*60)
	hours = int(seconds) // (60*60)
	seconds -= hours * (60*60)
	minutes = int(seconds) // (60)
	seconds -= minutes * (60)
	
	bits = []
	if days:
		bits.append( "1 day" if days == 1  else "%d days" % days)
	if hours:
		bits.append( "1 hour" if hours == 1 else "%d hours" % hours)
	if minutes:
		bits.append( "1 minute" if minutes == 1 else "%d minutes" % minutes)
	bits.append( "1 second" if seconds == 1 else "%.1f seconds" % seconds)
	
	return ", ".join(bits)
	
def associate_altmetric_data_with_documents(documents, altmetric_filename, filter_empty=True):
	with open(altmetric_filename) as f:
		altmetric_data = json.load(f)
	
	by_cord, by_pubmed, by_doi = {},{},{}
	for ad in altmetric_data:
		if ad['cord_uid']:
			by_cord[ad['cord_uid']] = ad['altmetric']
		if ad['pubmed_id']:
			by_pubmed[ad['pubmed_id']] = ad['altmetric']
		if ad['doi']:
			by_doi[ad['doi']] = ad['altmetric']
	
	for d in documents:
		altmetric_data = None
		if d['cord_uid'] in by_cord:
			altmetric_for_doc = by_cord[d['cord_uid']]
		elif d['pubmed_id'] in by_pubmed:
			altmetric_for_doc = by_pubmed[d['pubmed_id']]
		elif d['doi'] in by_doi:
			altmetric_for_doc = by_doi[d['doi']]
			
		if altmetric_data is None:
			continue
			
		if filter_empty and altmetric_for_doc['response'] == False:
			continue
		
		d['altmetric'] = altmetric_for_doc
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Tool to pull Altmetric data')
	parser.add_argument('--apiKeyFile',type=str,required=True,help='JSON file with API key')
	parser.add_argument('--documents',type=str,required=True,help='JSON file with documents')
	parser.add_argument('--popularOrRecent', action='store_true',help='Only track popular or recent publications')
	parser.add_argument('--prevData',type=str,required=False,help='JSON file with previous Altmetric data for documents')
	parser.add_argument('--outData',type=str,required=True,help='JSON file with Altmetric data for documents')
	args = parser.parse_args()
	
	with open(args.apiKeyFile) as f:
		apiKey = json.load(f)['key']
		
	with open(args.documents) as f:
		documents = json.load(f)
		
	if args.popularOrRecent:
		assert args.prevData, "Must provide previous data to use --popularOrRecent"
		associate_altmetric_data_with_documents(documents, args.prevData, filter_empty=False)
		
		popularOrRecent = []
		for d in documents:
			add = False
			if 'altmetric' in d:
				if d['altmetric'] is not None:
					history_1w = d['altmetric']['history']['1w']
					if history_1w > 10:
						# It's popular
						add = True
			else:
				# It's new
				add = True
				
			if d['publish_year']:
				pub_date = datetime.date(d['publish_year'],d['publish_month'] if d['publish_month'] else 1,d['publish_day'] if d['publish_day'] else 1)
				days_between = abs((pub_date-datetime.date.today()).days)
				
				# It's recent
				if days_between < 15:
					add = True
			
			if add:
				popularOrRecent.append(d)
				
		print("Found %d documents that are popular or recent" % len(popularOrRecent))
		documents = popularOrRecent
		
		
	output = []
	counts = Counter()
	start = time.time()
	for i,d in enumerate(documents):
	
		if (i%100) == 0:
			now = time.time()
			perc = 100*i/len(documents)
			
			time_so_far = (now-start)
			time_per_doc = time_so_far / (i+1)
			remaining_docs = len(documents) - i
			remaining_time = time_per_doc * remaining_docs
			total_time = time_so_far + remaining_time
			
			print("Completed %.1f%% (%d/%d)" % (perc,i,len(documents)))
			print("time_per_doc = %.4fs" % time_per_doc)
			print("remaining_docs = %d" % remaining_docs)
			print("time_so_far = %.1fs (%s)" % (time_so_far,nice_time(time_so_far)))
			print("remaining_time = %.1fs (%s)" % (remaining_time,nice_time(remaining_time)))
			print("total_time = %.1fs (%s)" % (total_time,nice_time(total_time)))
			print('-'*30)
	
		cord_uid = d['cord_uid']
		pubmed_id = d['pubmed_id']
		doi = d['doi']
		url = d['url']
		
		if doi:
			altmetric_url = "https://api.altmetric.com/v1/doi/%s?key=%s" % (doi,apiKey)
			method = 'doi'
		elif pubmed_id:
			altmetric_url = "https://api.altmetric.com/v1/pmid/%s?key=%s" % (pubmed_id,apiKey)
			method = 'pmid'
		elif url:
			altmetric_url = "https://api.altmetric.com/v1/uri/%s?key=%s" % (urllib.parse.quote(url),apiKey)
			method = 'uri'
		else:
			altmetric_url = None
			counts['no identifier'] += 1
			
		doc_data = {'cord_uid':cord_uid,'pubmed_id':pubmed_id,'doi':doi, 'altmetric':{'response':False}}
		if altmetric_url:
			response = requests.get(altmetric_url)
			if response.text == 'Not Found':
				counts['not found'] += 1
			else:
				response_json = json.loads(response.text)
				response_json['response'] = True
				doc_data['altmetric'] = response_json
				counts[method] += 1
		
		output.append(doc_data)
		
	print(counts)
		
	with open(args.outData,'w',encoding='utf8') as f:
		json.dump(output,f)
