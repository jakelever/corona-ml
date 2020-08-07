import os
import argparse
import json
from bs4 import BeautifulSoup
from collections import defaultdict
import sys
import re


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Collect relevant publication metadata from web scraped data')
	parser.add_argument('--inDir',type=str,required=True,help='Directory with JSON files')
	parser.add_argument('--prevData',type=str,required=False,help='Optional previous output, to avoid reparsing things')
	parser.add_argument('--outData',type=str,required=True,help='JSON file with metadata for each URL')
	args = parser.parse_args()
	
	prevData = {}
	if args.prevData and os.path.isfile(args.prevData):
		print("Loading previous data...")
		sys.stdout.flush()
		with open(args.prevData,'r',encoding='utf8') as f:
			prevData = json.load(f)
			
	inFiles = sorted( os.path.join(args.inDir,inFile) for inFile in os.listdir(args.inDir) if inFile.endswith('.json') )
	
	toStrip = {"robots","viewport","referrer","google-site-verification","sessionEvt-audSegment","sessionEvt-freeCntry","sessionEvt-idGUID","sessionEvt-individual","sessionEvt-instId","sessionEvt-instProdCode","sessionEvt-nejmSource","sessionEvt-offers","sessionEvt-prodCode","evt-ageContent","evt-artView","format-detection"}

	spanClassesToCheck = ['article-header__journal']
	  
	all_metadata = {}
	for inFile in inFiles:
		sublisting_file = re.sub(r'\.json$','.listing.txt',inFile)
		assert os.path.isfile(sublisting_file), "Couldn't find sublisting file: %s" % sublisting_file
		
		print("Loading listing %s..." % sublisting_file)
		with open(sublisting_file) as f:
			sublisting = set([ line.strip() for line in f ])
				
		needs_processing = []
		for url in sublisting:
			if url in prevData:
				all_metadata[url] = prevData[url]
			else:
				needs_processing.append(url)
		
		if len(needs_processing) == 0:
			print("No extra URLs need to be processed in %s" % inFile)
			continue
		
		print("Loading %s..." % inFile)
		sys.stdout.flush()
		with open(inFile) as f:
			raw_web_data = json.load(f)
			
		print("Processing %d URLs in %s..." % (len(needs_processing),inFile))
		sys.stdout.flush()
		for url in needs_processing:
			page = raw_web_data[url]
		
			if url in prevData:
				all_metadata[url] = prevData[url]
				continue
		
			meta_dict = defaultdict(list)
			meta_dict['status_code'] = page['status_code']
			
			if 'content' in page:
			
				meta_dict['resolved_url'] = page['resolved_url']
				meta_dict['url_history'] = page['url_history']
				
				soup = BeautifulSoup(page['content'], 'html.parser')
				metas = soup.find_all('meta')
				metas = [ m for m in metas if 'name' in m.attrs and 'content' in m.attrs ]
				
				for m in metas:
					name = m.attrs['name']
					value = m.attrs['content']
					
					if name in toStrip:
						continue
					
					assert not name in ['status_code','url_history','resolved_url']
						
					meta_dict[name].append(value)
					
				# JAMA (and maybe others?) store some data in span elements too
				spans = soup.find_all('span')
				spans = [ s for s in spans if 'data-attribute' in s.attrs and 'data-value' in s.attrs ]
				for s in spans:            
					name = s.attrs['data-attribute']
					value = s.attrs['data-value']
										
					assert not name in ['status_code','url_history','resolved_url']
						
					meta_dict[name].append(value)
					
				for className in spanClassesToCheck:
					for s in spans:
						if 'class' in s.attrs and s.attrs['class'] == className:
							meta_dict[className] = s.gettext()
				
			all_metadata[url] = dict(meta_dict)
			#break
	
	print("Saving data...")
	sys.stdout.flush()
	with open(args.outData,'w',encoding='utf8') as f:
		json.dump(all_metadata,f)
	