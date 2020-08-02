import argparse
import requests
import re
import time

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Poke the main pages of CoronaCentral to force a relaxed rebuild")
	args = parser.parse_args()
	
	print("Fetching list of pages to poke directly from CoronaCentral")
	response = requests.get('https://www.coronacentral.ai/')
	
	pages_to_poke = re.findall('"/[a-z]+"',response.text)
	pages_to_poke = sorted(set( page.strip('"') for page in pages_to_poke))
	
	assert len(pages_to_poke) > 10, "Found too few pages to poke. Something went wrong (%s)" % pages_to_poke
	
	print("Found %d pages to poke:" % len(pages_to_poke))
	print(pages_to_poke)

	for page in pages_to_poke:
		print("Poking %s... " % page)
		response = requests.get('https://www.coronacentral.ai' + page + '?notrack' )
		assert response.status_code == 200
		time.sleep(5)
	
	print("Complete.")
	