import os
import argparse
import json
from bs4 import BeautifulSoup
from collections import defaultdict


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Collect relevant publication metadata from web scraped data')
	parser.add_argument('--inDir',type=str,required=True,help='Directory with JSON files')
	parser.add_argument('--outData',type=str,required=True,help='JSON file with metadata for each URL')
	args = parser.parse_args()
	
	inFiles = sorted( inFile for inFile in os.listdir(args.inDir) if inFile.endswith('.json') )
	
	toStrip = {"robots","viewport","referrer","google-site-verification","sessionEvt-audSegment","sessionEvt-freeCntry","sessionEvt-idGUID","sessionEvt-individual","sessionEvt-instId","sessionEvt-instProdCode","sessionEvt-nejmSource","sessionEvt-offers","sessionEvt-prodCode","evt-ageContent","evt-artView","format-detection"}
	  
	spanClassesToCheck = ['article-header__journal']
	  
	all_metadata = {}
	for inFile in inFiles:
		print("Processing %s..." % inFile)
		with open(os.path.join(args.inDir,inFile)) as f:
			raw_web_data = json.load(f)
			
		for url,page in raw_web_data.items():
		
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
					
				for className in spanClassesToCheck
					for s in spans:
						if 'class' in s.attrs and s.attrs['class'] == className:
							meta_dict[className] = s.gettext()
				
			all_metadata[url] = dict(meta_dict)
			#break
	
	print("Saving data...")
	with open(args.outData,'w',encoding='utf8') as f:
		json.dump(all_metadata,f)
	