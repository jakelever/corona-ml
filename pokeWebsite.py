import argparse
import requests
import re
import time
#from requests.adapters import HTTPAdapter
#from requests.packages.urllib3.util.retry import Retry
import urllib3
import requests

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
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Poke the main pages of CoronaCentral to force a relaxed rebuild")
	parser.add_argument('--url',required=False,type=str,help='Alternative URL of CoronaCentral to poke (instead of coronacentral.ai)')
	args = parser.parse_args()
	
	s = requests.Session()
	
	print("Fetching list of pages to poke directly from CoronaCentral")
	if args.url:
		url = args.url.rstrip('/') + '/?notrack'
	else:
		url = 'https://www.coronacentral.ai/?notrack'
		
	#response = requests_retry_session(session=s).get(url)
	response = geturl(url)
	
	#pages_to_poke = re.findall(r'"/[^"]+"',response.text)
	pages_to_poke = re.findall(r'"/\w+"',response.text)
	pages_to_poke += re.findall('"/entity/[^"/]+/all"',response.text)
	pages_to_poke += re.findall(r'"/doc/[^"]+"',response.text)
	pages_to_poke = sorted(set( page.strip('"') for page in pages_to_poke))
	
	assert len(pages_to_poke) > 10, "Found too few pages to poke. Something went wrong (%s)" % pages_to_poke
	
	print("Found %d pages to poke:" % len(pages_to_poke))
	print(pages_to_poke)

	for page in pages_to_poke:
		print("Poking %s... " % page)
		url = 'https://www.coronacentral.ai' + page + '?notrack'
		#response = requests_retry_session(session=s).get(url)
		response = geturl(url)
		assert response.status_code == 200
		time.sleep(15)
	
	print("Complete.")
	
