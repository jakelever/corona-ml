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
	
	toStrip = {'status_code','url_history','resolved_url',"robots","viewport","referrer","google-site-verification","sessionEvt-audSegment","sessionEvt-freeCntry","sessionEvt-idGUID","sessionEvt-individual","sessionEvt-instId","sessionEvt-instProdCode","sessionEvt-nejmSource","sessionEvt-offers","sessionEvt-prodCode","evt-ageContent","evt-artView","format-detection"}

	spanClassesToCheck = set(['article-header__journal','primary-heading','highwire-article-collection-term'])
	
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
				spans = soup.find_all('span')
				
				# Get the metadata tags (with name and content attributes)
				metadata = [ (m.attrs['name'],m.attrs['content']) for m in metas if 'name' in m.attrs and 'content' in m.attrs ]
				
				# Some journals have span tags with data-attribute and data-value tags. Get those
				data_spans = [ (s.attrs['data-attribute'],s.attrs['data-value']) for s in spans if 'data-attribute' in s.attrs and 'data-value' in s.attrs ]
					
				# Also get a custom set of span tags with a specific class and get the text contents
				spans_with_class = [ s for s in spans if 'class' in s.attrs and s.attrs['class'] ]
				selected_spans = [ (class_name,s.get_text()) for s in spans_with_class for class_name in spanClassesToCheck if class_name in s.attrs['class'] ]
				
				#if selected_spans:
				#	print(selected_spans)
				#	assert False
				
				#for s in spans_with_class:
					#if 'class' in s.attrs:
					#	assert isinstance(s.attrs['class'],list)
					#print(s.attrs['class'])
					#print(dir(s))
					#assert False
				
				combined_data = metadata + data_spans + selected_spans
				
				# Filter for strings as name and value and remove any ones from the toStrip list
				combined_data = [ (name,value) for name,value in combined_data if isinstance(name,str) and isinstance(value,str) ]
				combined_data = [ (name,value) for name,value in combined_data if not name in toStrip ]
				combined_data = sorted(set(combined_data))
				
				for name,value in combined_data:
					meta_dict[name].append(value)
				# 
				
			all_metadata[url] = dict(meta_dict)
			#break
		#assert False
	
	print("Saving data...")
	sys.stdout.flush()
	with open(args.outData,'w',encoding='utf8') as f:
		json.dump(all_metadata,f)
	
