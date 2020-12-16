import twitter
from TwitterAPI import TwitterAPI
from threader import Threader

import json
from datetime import date
import urllib3
import requests
import time
import argparse

from collections import OrderedDict
from bs4 import BeautifulSoup
import urllib.parse
import random

def geturl(url,retries=10):
	headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

	response = None
	for retry in range(retries):
		try:
			response = requests.get(url,headers=headers)
			break
		except requests.exceptions.ConnectionError:
			print("Error: requests.exceptions.ConnectionError")
			pass
		except urllib3.exceptions.MaxRetryError:
			print("Error: urllib3.exceptions.MaxRetryError")
			pass
		except urllib3.exceptions.NewConnectionError:
			print("Error: urllib3.exceptions.NewConnectionError")
			pass
			
		time.sleep((retry+1)*3)
		
	if response is None:
		raise RuntimeError("Unable to connect to %s" % url)
	else:
		return response

def resolveurl(url,history=[]):
	response = geturl(url)	
	
	if response.status_code != 200:
		return None #{ 'status_code': response.status_code }
	
	try:
		soup = BeautifulSoup(response.text, 'html.parser')
	except:
		return url #{ 'status_code': 'ParseError' }
	
	metas = soup.find_all('meta')
	metas = [ m for m in metas if 'name' in m.attrs and 'content' in m.attrs ]
	
	response_history = history + [ h.url for h in response.history ]
	response_history = list(OrderedDict.fromkeys(response_history))
	
	redirectURLInputs = [ elem for elem in soup.find_all('input') if 'name' in elem.attrs and elem.attrs['name'] == 'redirectURL' and 'value' in elem.attrs ]
	if len(metas) == 0 and len(redirectURLInputs) == 1:
		redirectURL = urllib.parse.unquote(redirectURLInputs[0].attrs['value'])
		#print(redirectURL)
		return resolveurl(redirectURL,response_history)
		
	#assert False
	#print(len(metas), len(redirectURLInputs))
	
	return response.url	
		
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

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Tweet the top three trending articles')
	parser.add_argument('--documents',required=True,type=str,help='CoronaCentral documents')
	parser.add_argument('--altmetric',required=True,type=str,help='Altmetric data')
	parser.add_argument('--twitterApiKey',required=True,type=str,help='Twitter API credentials')
	args = parser.parse_args()
	
	print("Loading documents...")
	with open(args.documents) as f:
		documents = json.load(f)
		
	print("Loading Altmetric data...")
	associate_altmetric_data_with_documents(documents, args.altmetric, filter_empty=True)
	
	print("Finding trending documents...")
	today = date.today()

	trending = []

	for d in documents:
		if 'altmetric' in d:
			score_1day = d['altmetric']['history']['1d']
			publish_year = d['publish_year']
			if not publish_year:
				continue
				
			publish_month = d['publish_month'] if d['publish_month'] else 1
			publish_day = d['publish_day'] if d['publish_day'] else 1
			
			publish_date = date(publish_year, publish_month, publish_day)
			delta = today - publish_date
			
			if delta.days <= 14 and delta.days >= 0:
				trending.append( (score_1day,delta,d))
				
	trending = sorted(trending, key=lambda x:x[0], reverse=True)
	
	print("Preparing tweets and poking document pages...")
	messages = []

	first_preamble = ['The top three trending articles today are:', "CoronaCentral's top trending articles today are:","Today's top three trending articles are:"]
	second_preamble = ['And second:', 'The second is:', "No 2 is:"]
	third_preamble = ['And third:', 'The third is:', "No 3 is:"]

	#preambles = ['The top three trending articles today are:', 'And second:', 'And third:']
	preambles = [ random.choice(first_preamble), random.choice(second_preamble), random.choice(third_preamble) ]

	message_size_limit = 280 - 25 

	print("Tweets:")
	for i,(score_1day,delta,d) in enumerate(trending[:3]):
		url,cc_url = None,None
		if d['doi']:
			#url = "https://coronacentral.ai/doc/doi/%s" % d['doi']
			url = "https://doi.org/%s" % d['doi']
		elif d['pubmed_id']:
			#url = "https://coronacentral.ai/doc/pubmed_id/%s" % d['pubmed_id']
			url = "https://pubmed.ncbi.nlm.nih.gov/%s" % d['pubmed_id']
		elif d['url']:
			url = d['url']
		elif d['cord_uid']:
			url = "https://coronacentral.ai/doc/cord_uid/%s" % d['cord_uid']

		if d['doi']:
			cc_url = "https://coronacentral.ai/doc/doi/%s" % d['doi']
		elif d['pubmed_id']:
			cc_url = "https://coronacentral.ai/doc/pubmed_id/%s" % d['pubmed_id']
		
		message = "%s %s" % (preambles[i],d['title'])
		
		if len(message) >= (message_size_limit-3):
			message = message[:message_size_limit] + '...'

		# Resolve redirections to get the actual URL
		#response = geturl(url)
		#url = response.url

		# Resolve redirections to get the actual URL
		url = resolveurl(url)

		if not url:
			# Ping the CoronaCentral server to build the page
			_ = resolveurl(cc_url)
			time.sleep(10)

			url = cc_url
		
		if url:
			message += " " + url
			
		#print(message)
		messages.append(message)
		
		#print(response)
		#print(response.url)
		#print(dir(response))
		#assert False
		time.sleep(5)
    
	#print("Giving server time to render pages")
	#time.sleep(30)

	final_message = [ "See more trending coronavirus research articles at CoronaCentral https://coronacentral.ai/trending", "Check out more trending coronavirus research here https://coronacentral.ai/trending", "More trending articles can be found at CoronaCentral https://coronacentral.ai/trending"]

	#messages.append(random.choice(final_message))

	for m in messages:
		print(m)
		print('-'*30)

	if True:	
		print("Connecting to Twitter API...")
		with open(args.twitterApiKey) as f:
			twitter_api_key = json.load(f)
			consumer_key = twitter_api_key['consumer_key']
			consumer_secret = twitter_api_key['consumer_secret']
			access_token = twitter_api_key['access_token']
			access_token_secret = twitter_api_key['access_token_secret']
		
		api = twitter.Api(consumer_key=consumer_key,
			consumer_secret=consumer_secret,
			access_token_key=access_token,
			access_token_secret=access_token_secret,
			tweet_mode='extended',
			sleep_on_rate_limit=True)

	#	keys = dict(consumer_key=consumer_key,
	#            consumer_secret=consumer_secret,
	#            access_token_key=access_token,
	#            access_token_secret=access_token_secret)
	#
	#	api = TwitterAPI(**keys)
			
		print("Sending tweets...")
		prev_status_id = None
		for message in messages:
			if prev_status_id:
				status = api.PostUpdate(message, in_reply_to_status_id=prev_status_id,auto_populate_reply_metadata=True)
			else:
				status = api.PostUpdate(message)

			prev_status_id = status.id
			time.sleep(20)

		#th = Threader(messages, api, wait=2)
		#th.send_tweets()
		
	print("Done")
	
