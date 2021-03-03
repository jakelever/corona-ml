import argparse
import json
import re
from collections import Counter

def predictTrial(abstractLower):
    trialNumber = re.search(r'ctr[0-9]+',abstractLower)
    nihTrialNumber = re.search(r'nct\s*[0-9]+',abstractLower)
    
    decision = bool(trialNumber or nihTrialNumber)
    return decision

def main():
	parser = argparse.ArgumentParser('Annotate documents using rules for extra categories such as clinical trials')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
	
	print("Loading documents...")
	with open(args.inJSON) as f:
		documents = json.load(f)

	beforeCategoryCount = Counter( c for d in documents if 'categories' in d for c in d['categories'] )

	nonResearchArticleTypes = ['Review','Book chapter','Comment/Editorial','Retracted','CDC Weekly Report','News']
	allArticleTypes = nonResearchArticleTypes + ['Research','Meta-analysis']
		
	trialCount = 0
	for d in documents:
		abstractLower = d['abstract'].lower()
		predictedTrial = predictTrial(abstractLower)
		
		annotatedTrial = 'Clinical Trial' in d['annotations']
		meshTrial = 'pub_type' in d and any('Clinical Trial' in pt for pt in d['pub_type'])
		
		if not 'categories' in d:
			d['categories'] = []
		
		if annotatedTrial or meshTrial or predictedTrial:
			d['categories'].append('Clinical Trials')
			trialCount += 1

		isCDCWeeklyReport = d['journal'] == 'MMWR. Morbidity and Mortality Weekly Report'
		if isCDCWeeklyReport:
			d['categories'].append('CDC Weekly Report')

		if re.search(r'Chapter \d',d['title'], re.IGNORECASE):
			d['categories'].append('Book chapter')

		if 'Meta-analysis' in d['categories'] and 'Review' in d['categories']:
			d['categories'].remove('Review')

		if not any(at in d['categories'] for at in nonResearchArticleTypes):
			d['categories'].append('Research')

		if d['inferred_article_type']:
			d['categories'] = [ c for c in d['categories'] if not c in allArticleTypes ]
			d['categories'].append(d['inferred_article_type'])

		d['categories'] = sorted(set(d['categories']))	

	afterCategoryCount = Counter( c for d in documents if 'categories' in d for c in d['categories'] )
	
	diffCount = afterCategoryCount - beforeCategoryCount

	print("Added category counts:")
	print(diffCount)		
		
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)

if __name__ == '__main__':
	main()

