import argparse
import json
import requests
import urllib.parse
from collections import Counter,defaultdict
import time
import datetime
import urllib.parse
import random
from collections import OrderedDict
import sys
import os
import re

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
	tidied_metadata['content'] = response.text

	return tidied_metadata

	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Tool to pull Altmetric data')
	parser.add_argument('--documents',type=str,required=True,help='JSON file with documents')
	parser.add_argument('--webDir',type=str,required=True,help='Directory with JSON files containing web data')
	parser.add_argument('--outFlagFile',type=str,required=True,help='A useless file to mark that this is complete')
	args = parser.parse_args()
	
	#ray.init()
	
	with open(args.documents) as f:
		documents = json.load(f)

	assert os.path.isdir(args.webDir)
	listing_file = os.path.join(args.webDir,'listings.txt')
	predone_urls = []
	if os.path.isfile(listing_file):
		print("Found listing file...")
		sys.stdout.flush()
		with open(listing_file) as f:
			predone_urls = [ line.strip() for line in f ]
			predone_urls = set(predone_urls)
	else:
		prev_files = [ os.path.join(args.webDir,f) for f in os.listdir(args.webDir) if f.endswith('.json') ]
		for prev_file in sorted(prev_files):
			print("Loading previous file %s to check URLs" % prev_file)
			sys.stdout.flush()
			with open(prev_file) as f:
				prev_data = json.load(f)
				predone_urls += list(prev_data.keys())
				
			sublisting_file = re.sub(r'\.json$','.listing.txt',prev_file)
			if not os.path.isfile(sublisting_file):
				with open(sublisting_file,'w') as f:
					for url in sorted(prev_data.keys()):
						f.write("%s\n" % url)
			
		predone_urls = set(predone_urls)
		
		print("Saving listing file with predone")
		sys.stdout.flush()
		with open(listing_file,'w') as f:
			for url in sorted(predone_urls):
				f.write("%s\n" % url)
			
	print("Found %d predone URLS" % len(predone_urls))
	
	#scraped = [ scrapeURL(d['doi'] for d in documents[:100] ]
		
	#url = 'https://doi.org/10.1056/NEJMoa2022483'
	
	#scraped = scrapeURL(url)
	
	scraped = {}
	
	urls = ['https://doi.org/%s' % d['doi'] for d in documents if d['doi'] ]
	urls += [ d['url'] for d in documents if d['url'] and not 'pubmed' in d['url'] ]
	urls += [ url for url in urls if not url.endswith('.pdf') ]
	urls = sorted(set(urls))
	
	print("Documents contain %d URLs" % len(urls))
	
	needs_doing = [ url for url in urls if not url in predone_urls ]
	
	print("Need to process %d URLs" % len(needs_doing))
	sys.stdout.flush()
	
	random.seed(0)
	random.shuffle(needs_doing)
	
	#with open('url_list.json','w') as f:
	#	json.dump(needs_doing,f,indent=2,sort_keys=True)
	#assert False
	
	#urls = urls[:250]
	
	start = time.time()
	for i,url in enumerate(needs_doing):

		if (i%1000) == 0:
			#waypointFile = "%s.%08d.json" % (args.outData.replace('.json',''),i)
			waypointFile = "waypoint.json"
			print("Saving waypoint (%s)..." % waypointFile)
			with open(waypointFile,'w',encoding='utf8') as f:
				json.dump(scraped,f)
		
		if (i%10) == 0:
			now = time.time()
			perc = 100*i/len(needs_doing)
			
			time_so_far = (now-start)
			time_per_doc = time_so_far / (i+1)
			remaining_docs = len(needs_doing) - i
			remaining_time = time_per_doc * remaining_docs
			total_time = time_so_far + remaining_time
			
			print("Completed %.1f%% (%d/%d)" % (perc,i,len(needs_doing)))
			print("time_per_doc = %.4fs" % time_per_doc)
			print("remaining_docs = %d" % remaining_docs)
			print("time_so_far = %.1fs (%s)" % (time_so_far,nice_time(time_so_far)))
			print("remaining_time = %.1fs (%s)" % (remaining_time,nice_time(remaining_time)))
			print("total_time = %.1fs (%s)" % (total_time,nice_time(total_time)))
			print('-'*30)
			print(Counter( d['status_code'] for d in scraped.values() ))
			print()
			sys.stdout.flush()
		
		scraped[url] = scrapeURL(url)
		#print(d['doi'], scraped[url]['status_code'], len(scraped[url]))
	
	#print(json.dumps(scraped,indent=2,sort_keys=True))
	
			#break
	#print(metas)
	
	if len(scraped) > 0:
		outFilename = None
		i = 0
		while True:
			outFilename = os.path.join(args.webDir,"update_%08d.json" % i)
			i += 1
			if not os.path.isfile(outFilename):
				break
		
		print("Saving data to %s..." % outFilename)
		with open(outFilename,'w',encoding='utf8') as f:
			json.dump(scraped,f)
			
		sublisting_file = re.sub(r'\.json$','.listing.txt',outFilename)
		with open(sublisting_file,'w') as f:
			for url in sorted(scraped.keys()):
				f.write("%s\n" % url)
		
	print("Updating listing file...")
	all_urls = sorted(set(list(scraped.keys()) + list(predone_urls)))
	with open(listing_file,'w') as f:
		for url in all_urls:
			f.write("%s\n" % url)
			
	print("Saving flag file")
	with open(args.outFlagFile,'w') as f:
		f.write("Done\n")
		#json.dump(scraped,f,indent=2,sort_keys=True)
