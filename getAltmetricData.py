import argparse
import json
import requests
import urllib.parse
from collections import Counter
import time
	
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
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Tool to pull Altmetric data')
	parser.add_argument('--apiKeyFile',type=str,required=True,help='JSON file with API key')
	parser.add_argument('--documents',type=str,required=True,help='JSON file with documents')
	parser.add_argument('--outData',type=str,required=True,help='JSON file with Altmetric data for documents')
	args = parser.parse_args()
	
	with open(args.apiKeyFile) as f:
		apiKey = json.load(f)['key']
		
	with open(args.documents) as f:
		documents = json.load(f)
		
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
		
		#doi = False
		#pubmed_id = False
		
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
			counts['no identifier'] += 1
			continue
			
		response = requests.get(altmetric_url)
		if response.text == 'Not Found':
			counts['not found'] += 1
			continue
		
		doc_data = json.loads(response.text)
		#print(data)
		counts[method] += 1
		
		doc_data['identifiers'] = {'cord_uid':cord_uid,'pubmed_id':pubmed_id,'doi':doi}
		output.append(doc_data)
		#break
		
	print(counts)
		
	with open(args.outData,'w',encoding='utf8') as f:
		json.dump(output,f)
