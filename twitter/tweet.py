import twitter
import json
from datetime import date
import urllib3
import requests
import time

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
	
def geturl(url,retries=10):
	response = None
	for retry in range(retries):
		try:
			response = requests.get(url)
			break
		except requests.exceptions.ConnectionError:
			pass
		except urllib3.exceptions.MaxRetryError:
			pass
		except urllib3.exceptions.NewConnectionError:
			pass
			
		time.sleep((retry+1)*3)
		
	if response is None:
		raise RuntimeError("Unable to connect to %s" % url)
	else:
		return response
		
def associate_altmetric_data_with_documents(documents, altmetric_filename, filter_empty):
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
		altmetric_for_doc = None
		if d['cord_uid'] and d['cord_uid'] in by_cord:
			altmetric_for_doc = by_cord[d['cord_uid']]
		elif d['pubmed_id'] and d['pubmed_id'] in by_pubmed:
			altmetric_for_doc = by_pubmed[d['pubmed_id']]
		elif d['doi'] and d['doi'] in by_doi:
			altmetric_for_doc = by_doi[d['doi']]
			
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
	preambles = ['The top three trending articles today are:', 'And second:', 'And third:']

	message_size_limit = 280 - 25 

	print("Tweets:")
	for i,(score_1day,delta,d) in enumerate(trending[:3]):
		url = None
		if d['doi']:
			url = "https://coronacentral.ai/doc/doi/%s" % d['doi']
		elif d['pubmed_id']:
			url = "https://coronacentral.ai/doc/pubmed_id/%s" % d['pubmed_id']
		elif d['cord_uid']:
			url = "https://coronacentral.ai/doc/cord_uid/%s" % d['cord_uid']
		
		message = "%s %s" % (preambles[i],d['title'])
		
		if len(message) >= (message_size_limit-3):
			message = message[:message_size_limit] + '...'
		
		if url:
			message += " " + url
			
		print(message)
		messages.append(message)
		
		response = geturl(url)
		print(response)
		time.sleep(5)
    
	print("Giving server time to render pages")
	time.sleep(30)
	
	print("Sending tweets...")
	prev_status_id = None
	for message in messages:
		status = api.PostUpdate(message, in_reply_to_status_id=prev_status_id)
		prev_status_id = status.id
		
	print("Done")
	