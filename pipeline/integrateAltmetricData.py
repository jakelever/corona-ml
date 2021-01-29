import argparse
import json
	
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
	
def main():
	parser = argparse.ArgumentParser(description='Integrate Altmetric data with CoronaCentral documents')
	parser.add_argument('--documents',type=str,required=True,help='JSON file with documents')
	parser.add_argument('--altmetricData',type=str,required=True,help='JSON file with Altmetric data for documents')
	parser.add_argument('--outData',type=str,required=True,help='JSON file with Altmetric data for documents')
	args = parser.parse_args()
	
	with open(args.documents) as f:
		documents = json.load(f)
		
	print("Loaded %d documents" % len(documents))
		
	associate_altmetric_data_with_documents(documents, args.altmetricData, filter_empty=False)

	altmetric_count = len( [ d for d in documents if 'altmetric' in d ] )

	print("Integrated Altmetric data for %d documents" % altmetric_count)
		
	print("Saving data...")
	with open(args.outData,'w',encoding='utf8') as f:
		json.dump(documents,f,indent=2,sort_keys=True)

if __name__ == '__main__':
	main()

