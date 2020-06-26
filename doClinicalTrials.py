import argparse
import json
import re

def predictTrial(abstractLower):
    clinicalTrialsGov = 'clinicaltrials.gov' in abstractLower
    trialNumber = re.search(r'ctr[0-9]+',abstractLower)
    nihTrialNumber = re.search(r'nct[0-9]+',abstractLower)
    openLabel = 'open-label' in abstractLower or 'open label' in abstractLower
    
    decision = bool(clinicalTrialsGov or trialNumber or nihTrialNumber or openLabel)
    decision = bool(trialNumber)
    return decision

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Annotate documents that are likely clinical trials')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
	
	print("Loading documents...")
	with open(args.inJSON) as f:
		documents = json.load(f)
		
	for d in documents:
		abstractLower = d['abstract'].lower()
		predictedTrial = predictTrial(abstractLower)
		
		annotatedTrial = 'Clinical Trial' in d['annotations']
		meshTrial = 'pub_type' in d and any('Clinical Trial' in pt for pt in d['pub_type'])
		
		if not 'topics' in d:
			d['topics'] = []
		
		if annotatedTrial or meshTrial or predictedTrial:
			d['topics'].append('Clinical Trials')
		
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)