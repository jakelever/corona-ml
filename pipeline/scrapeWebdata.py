import argparse
import json
import requests
import urllib.parse
from collections import Counter
import time
import random
from collections import OrderedDict,defaultdict
import sys
import os
import re
from tqdm import tqdm
import gzip

from bs4 import BeautifulSoup

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

toStrip = {'status_code','url_history','resolved_url',"robots","viewport","referrer","google-site-verification","sessionEvt-audSegment","sessionEvt-freeCntry","sessionEvt-idGUID","sessionEvt-individual","sessionEvt-instId","sessionEvt-instProdCode","sessionEvt-nejmSource","sessionEvt-offers","sessionEvt-prodCode","evt-ageContent","evt-artView","format-detection"}

spanClassesToCheck = set(['article-header__journal','primary-heading','highwire-article-collection-term'])

def parseContent(content):
	soup = BeautifulSoup(content, 'html.parser')
	metas = soup.find_all('meta')
	spans = soup.find_all('span')
	
	# Get the metadata tags (with name and content attributes)
	metadata = [ (m.attrs['name'],m.attrs['content']) for m in metas if 'name' in m.attrs and 'content' in m.attrs ]
	
	# Some journals have span tags with data-attribute and data-value tags. Get those
	data_spans = [ (s.attrs['data-attribute'],s.attrs['data-value']) for s in spans if 'data-attribute' in s.attrs and 'data-value' in s.attrs ]
		
	# Also get a custom set of span tags with a specific class and get the text contents
	spans_with_class = [ s for s in spans if 'class' in s.attrs and s.attrs['class'] ]
	selected_spans = [ (class_name,s.get_text()) for s in spans_with_class for class_name in spanClassesToCheck if class_name in s.attrs['class'] ]
	
	combined_data = metadata + data_spans + selected_spans
	
	# Filter for strings as name and value and remove any ones from the toStrip list
	combined_data = [ (name,value) for name,value in combined_data if isinstance(name,str) and isinstance(value,str) ]
	combined_data = [ (name,value) for name,value in combined_data if not name in toStrip ]
	combined_data = sorted(set(combined_data))
	
	meta_dict = defaultdict(list)
	for name,value in combined_data:
		meta_dict[name].append(value)
	meta_dict = dict(meta_dict)

	return meta_dict
	
def scrapeURL(url,history=[]):
	headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

	try:
		response = requests.get(url, headers=headers, timeout=10)
	except requests.exceptions.Timeout:
		return { 'status_code': 'Timeout' }
	except requests.exceptions.TooManyRedirects:
		return { 'status_code': 'TooManyRedirects' }
	except requests.exceptions.RequestException:
		return { 'status_code': 'RequestException' }


	if response.status_code != 200:
		return { 'status_code': response.status_code }

	try:
		soup = BeautifulSoup(response.text, 'html.parser')
	except:
		return { 'status_code': 'ParseError' }

	metas = soup.find_all('meta')
	metas = [ m for m in metas if 'name' in m.attrs and 'content' in m.attrs ]

	response_history = history + [ h.url for h in response.history ]
	response_history = list(OrderedDict.fromkeys(response_history))

	redirectURLInputs = [ elem for elem in soup.find_all('input') if 'name' in elem.attrs and elem.attrs['name'] == 'redirectURL' and 'value' in elem.attrs ]
	if len(metas) == 0 and len(redirectURLInputs) == 1:
		redirectURL = urllib.parse.unquote(redirectURLInputs[0].attrs['value'])
		return scrapeURL(redirectURL,response_history)

	tidied_metadata = {}
	tidied_metadata['resolved_url'] = response.url
	tidied_metadata['url_history'] = response_history
	tidied_metadata['status_code'] = 200

	tidied_metadata['parsed'] = parseContent(response.text)

	return tidied_metadata

def scrapeDocument(d):
	filtered_urls = [ u for u in d['urls'] if u and not ('ncbi.nlm.nih.gov' in u or u.endswith('.pdf')) ]

	d['webmetadata'] = None

	for u in filtered_urls:
		webmetadata = scrapeURL(u)
		d['webmetadata'] = webmetadata
		if webmetadata['status_code'] == 200:
			break

	return d

def tidyURLs(d):
	urls = [ u.strip() for u in d['url'].split(';') ]
	if d['doi']:
		urls.append('https://doi.org/%s' % d['doi'])
	urls = [ u for u in urls if u ]
	urls = sorted(set(urls))

	d['urls'] = urls

def main():
	parser = argparse.ArgumentParser(description='Tool to pull Altmetric data')
	parser.add_argument('--inJSON',type=str,required=True,help='JSON file with documents')
	parser.add_argument('--prevJSON',type=str,required=False,help='Optional previously processed output (to save time)')
	parser.add_argument('--outJSON',type=str,required=True,help='JSON file with documents plus web data')
	args = parser.parse_args()

	scraped = {}

	url_map = {}
	if args.prevJSON and os.path.isfile(args.prevJSON):
		print("Loading previous output...")
		sys.stdout.flush()

		with gzip.open(args.prevJSON,'rt') as f:
			prev_documents = json.load(f)

		for d in prev_documents:
			tidyURLs(d)

		for d in prev_documents:
			#url_key = (d['url'],d['doi'])
			#url_map[url_key] = d['webmetadata']
			for u in d['urls']:
				url_map[u] = d['webmetadata']

	print("Loading documents...")
	sys.stdout.flush()

	with gzip.open(args.inJSON,'rt') as f:
		documents = json.load(f)

	for d in documents:
		tidyURLs(d)

	needs_doing = []
	already_done = []
	for d in documents:
		existing_webmetadata = False
		for u in d['urls']:
			if u in url_map:
				d['webmetadata'] = url_map[u]
				existing_webmetadata = True
				break

		#url_key = (d['url'],d['doi'])
		#if url_key in url_map:
		#	d['webmetadata'] = url_map[url_key]

		if len(d['urls']) == 0:
			d['webmetadata'] = None
			existing_webmetadata = True

		if existing_webmetadata:
			already_done.append(d)
		else:
			needs_doing.append(d)
		

	print("%d documents previously processed" % len(already_done))
	print("%d documents to be processed" % len(needs_doing))
	print()
	sys.stdout.flush()

	random.seed(0)
	random.shuffle(needs_doing)
	
	start_time = time.time()

	print("Starting....")
	sys.stdout.flush()

	new_results = []
	for doc in tqdm(needs_doing):
		new_results.append( scrapeDocument(doc) )
	needs_doing = new_results

	output_documents = already_done + needs_doing

	assert len(output_documents) == len(documents)
	assert all( 'webmetadata' in d for d in output_documents ), "Some documents do not contain webmetadata output"
	
	print("Saving...")
	sys.stdout.flush()
	with gzip.open(args.outJSON,'wt') as f:
		json.dump(output_documents,f,indent=2,sort_keys=True)

	print("Done.")

if __name__ == '__main__':
	main()
