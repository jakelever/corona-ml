import argparse
import json
import requests
import urllib.parse
import time
import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import sys
from multiprocessing import Pool

# From: https://www.peterbe.com/plog/best-practice-with-retries-with-requests
def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
	session = session or requests.Session()
	retry = Retry(
		total=retries,
		read=retries,
		connect=retries,
		backoff_factor=backoff_factor,
		status_forcelist=status_forcelist,
	)
	adapter = HTTPAdapter(max_retries=retry)
	session.mount('http://', adapter)
	session.mount('https://', adapter)
	return session
	
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
	
def estimateTime(start_time,num_completed,num_total):
	now = time.time()
	perc = 100*num_completed/num_total
	
	time_so_far = (now-start_time)
	time_per_item = time_so_far / (num_completed+1)
	remaining_items = num_total - num_completed
	remaining_time = time_per_item * remaining_items
	total_time = time_so_far + remaining_time
	
	print("Completed %.1f%% (%d/%d)" % (perc,num_completed,num_total))
	print("time_per_item = %.4fs" % time_per_item)
	print("remaining_items = %d" % remaining_items)
	print("time_so_far = %.1fs (%s)" % (time_so_far,nice_time(time_so_far)))
	print("remaining_time = %.1fs (%s)" % (remaining_time,nice_time(remaining_time)))
	print("total_time = %.1fs (%s)" % (total_time,nice_time(total_time)))
	print('-'*30)
	print()
	sys.stdout.flush()

def associate_altmetric_data_with_documents(documents, altmetric_filename, filter_empty):
	with open(altmetric_filename) as f:
		altmetric_data = json.load(f)
	
	by_cord, by_pubmed, by_doi, by_url = {},{},{},{}
	for ad in altmetric_data:
		if ad['cord_uid']:
			by_cord[ad['cord_uid']] = ad['altmetric']
		if ad['pubmed_id']:
			by_pubmed[ad['pubmed_id']] = ad['altmetric']
		if ad['doi']:
			by_doi[ad['doi']] = ad['altmetric']
		if ad['url']:
			by_url[ad['url']] = ad['altmetric']
	
	for d in documents:
		altmetric_for_doc = None
		if d['cord_uid'] and d['cord_uid'] in by_cord:
			altmetric_for_doc = by_cord[d['cord_uid']]
		elif d['pubmed_id'] and d['pubmed_id'] in by_pubmed:
			altmetric_for_doc = by_pubmed[d['pubmed_id']]
		elif d['doi'] and d['doi'] in by_doi:
			altmetric_for_doc = by_doi[d['doi']]
		elif d['url'] and d['url'] in by_url:
			altmetric_for_doc = by_url[d['url']]
			
		if altmetric_for_doc is None:
			continue
		elif filter_empty and altmetric_for_doc['response'] == False:
			continue
		
		d['altmetric'] = altmetric_for_doc
		
def get_altmetric_for_doc(apiKey,d):
	cord_uid = d['cord_uid']
	pubmed_id = d['pubmed_id']
	doi = d['doi']
	arxiv_id = d['arxiv_id'] if 'arxiv_id' in d else None
	url = d['url']
	
	if doi:
		altmetric_url = "https://api.altmetric.com/v1/doi/%s?key=%s" % (doi,apiKey)
		method = 'doi'
	elif pubmed_id:
		altmetric_url = "https://api.altmetric.com/v1/pmid/%s?key=%s" % (pubmed_id,apiKey)
		method = 'pmid'
	elif arxiv_id:
		altmetric_url = "https://api.altmetric.com/v1/arxiv/%s?key=%s" % (arxiv_id,apiKey)
		method = 'arxiv'
	elif url:
		altmetric_url = "https://api.altmetric.com/v1/uri/%s?key=%s" % (urllib.parse.quote(url),apiKey)
		method = 'uri'
	else:
		altmetric_url = None
		#counts['no identifier'] += 1
		
	s = requests.Session()
		
	doc_data = {'cord_uid':cord_uid,'pubmed_id':pubmed_id,'doi':doi,'arxiv_id':arxiv_id,'url':url,'altmetric':{'response':False}}
	if altmetric_url:
		response = None
		try:
			response = requests_retry_session(session=s).get(altmetric_url)
		except requests.exceptions.RetryError:
			pass

		if response is None or response.text == 'Not Found':
			#counts['not found'] += 1
			pass
		else:
			assert response.status_code == 200
			response_json = json.loads(response.text)
			response_json['response'] = True
			doc_data['altmetric'] = response_json
			#counts[method] += 1
			
	#print(altmetric_url, doc_data)
			
	return doc_data
	
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
		
	print("Loaded %d documents" % len(documents))
		
	if args.popularOrRecent:
		assert args.prevData, "Must provide previous data to use --popularOrRecent"
		associate_altmetric_data_with_documents(documents, args.prevData, filter_empty=False)
		
		has_altmetric_response = len( [ d for d in documents if 'altmetric' in d ] )
		has_altmetric_and_score = len( [ d for d in documents if 'altmetric' in d and 'score' in d['altmetric'] ] )
		
		print("Found %d documents with Altmetric responses" % has_altmetric_response)
		print("Found %d documents with Altmetric responses and scores" % has_altmetric_and_score)
		
		popularOrRecent = []
		for d in documents:
			add = False
			if 'altmetric' in d:
				if d['altmetric']['response'] == True:
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
		
	print("Starting processing of %d documents..." % len(documents))
		
	start_time = time.time()
	output = []
	if len(documents) > 0:
		with Pool(5) as pool:
			new_results = [ pool.apply_async(get_altmetric_for_doc, (apiKey,doc,)) for doc in documents ]
			while True:
				num_completed = len( [ r for r in new_results if r.ready() ] )
				todo = len(documents) - num_completed

				estimateTime(start_time, num_completed, len(documents))
				if todo == 0:
					break
				time.sleep(5)

			output = [ r.get() for r in new_results ]
	
	print("Saving data...")
	with open(args.outData,'w',encoding='utf8') as f:
		json.dump(output,f,indent=2,sort_keys=True)

