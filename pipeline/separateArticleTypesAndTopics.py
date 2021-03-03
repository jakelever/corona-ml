import argparse
import json
from collections import Counter

def main():
	parser = argparse.ArgumentParser('Separate out the predicated categories into article types and topics')
	parser.add_argument('--inJSON',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--outJSON',required=True,type=str,help='JSON file with processed documents')
	args = parser.parse_args()

	article_types = {'Research','Meta-analysis','Review','Book chapter','Comment/Editorial','Retracted','CDC Weekly Report','News'}

	print("Loading...")
	with open(args.inJSON) as f:
		documents = json.load(f)

	articletype_counts = Counter()
	multi_articletype_counts = Counter()
	articletype_count_counts = Counter()
	topic_counts = Counter()

	print("Processing...")
		
	for d in documents:
		d['articletypes'] = [ c for c in d['categories'] if c in article_types ]
		d['topics'] = [ c for c in d['categories'] if c not in article_types ]

		del d['categories']

		articletype_counts += Counter(d['articletypes'])
		topic_counts += Counter(d['topics'])

		articletype_count_counts[len(d['articletypes'])] += 1
		if len(d['articletypes']) > 1:
			multi_articletype_counts[tuple(d['articletypes'])] += 1

	print("articletype_count_counts:", articletype_count_counts)
	print("multi_articletype_counts:", multi_articletype_counts)
	print("articletype_counts:", articletype_counts)
	print("topic_counts:", topic_counts)
			
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)
	
if __name__ == '__main__':
	main()

