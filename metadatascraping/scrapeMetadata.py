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
		#print(redirectURL)
		return scrapeURL(redirectURL,response_history)
		
	#assert False
	#print(len(metas), len(redirectURLInputs))
	
	
	tidied_metadata = defaultdict(list)
	#tidied_metadata['url'] = url
	tidied_metadata['resolved_url'] = response.url
	tidied_metadata['url_history'] = response_history
	tidied_metadata['status_code'] = 200
	for m in metas:
		name = m.attrs['name']
		content = m.attrs['content']
		
		assert not name in ['resolved_url','status_code','url_history'], "Clash found in url: %s" % url
		
		if name == 'Generator' and content.startswith('Drupal'):
			continue
		
		data = {'name':name, 'content':content}
		tidied_metadata[name].append(content)
		
	return dict(tidied_metadata)
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Tool to pull Altmetric data')
	parser.add_argument('--documents',type=str,required=True,help='JSON file with documents')
	parser.add_argument('--outData',type=str,required=True,help='JSON file with Altmetric data for documents')
	args = parser.parse_args()
	
	#ray.init()
	
	with open(args.documents) as f:
		documents = json.load(f)
	
	#scraped = [ scrapeURL(d['doi'] for d in documents[:100] ]
		
	#url = 'https://doi.org/10.1056/NEJMoa2022483'
	
	#scraped = scrapeURL(url)
	
	scraped = {}
	
	urls = ['https://doi.org/%s' % d['doi'] for d in documents if d['doi'] ]
	urls += [ d['url'] for d in documents if d['url'] and not 'pubmed' in d['url'] ]
	urls = sorted(set(urls))
	
	random.seed(0)
	random.shuffle(urls)
	
	urls = urls[:250]
	
	start = time.time()
	for i,url in enumerate(urls):
		
		if (i%10) == 0:
			now = time.time()
			perc = 100*i/len(urls)
			
			time_so_far = (now-start)
			time_per_doc = time_so_far / (i+1)
			remaining_docs = len(urls) - i
			remaining_time = time_per_doc * remaining_docs
			total_time = time_so_far + remaining_time
			
			print("Completed %.1f%% (%d/%d)" % (perc,i,len(urls)))
			print("time_per_doc = %.4fs" % time_per_doc)
			print("remaining_docs = %d" % remaining_docs)
			print("time_so_far = %.1fs (%s)" % (time_so_far,nice_time(time_so_far)))
			print("remaining_time = %.1fs (%s)" % (remaining_time,nice_time(remaining_time)))
			print("total_time = %.1fs (%s)" % (total_time,nice_time(total_time)))
			print('-'*30)
		
		scraped[url] = scrapeURL(url)
		#print(d['doi'], scraped[url]['status_code'], len(scraped[url]))
	
	#print(json.dumps(scraped,indent=2,sort_keys=True))
	
			#break
	#print(metas)
	
	print("Saving data...")
	with open(args.outData,'w',encoding='utf8') as f:
		json.dump(scraped,f)
		#json.dump(scraped,f,indent=2,sort_keys=True)
