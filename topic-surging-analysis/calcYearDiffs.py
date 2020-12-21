import argparse
from collections import Counter
import sys
import json

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Calculate the year-on-year differences in entity mention counts')
	parser.add_argument('--counts',required=True,type=str,help='File with entity counts by year')
	parser.add_argument('--mapping',required=True,type=str,help='MeSH mapping')
	parser.add_argument('--outFile',required=True,type=str,help='Output file')
	args = parser.parse_args()

	entities = set()
	years = set()
	counts = Counter()

	with open(args.mapping) as f:
		mapping = json.load(f)

	print("Loading counts...")
	sys.stdout.flush()
	with open(args.counts) as f:
		for lineno,line in enumerate(f):
			count,year,entity_type,entity_id = line.strip('\n').split('\t')
			count = int(count)
			year = int(year)

			entities.add((entity_type,entity_id))
			years.add(year)

			counts[ (year,entity_type,entity_id) ] = count

			#if lineno > 100000:
			#	break

	years = sorted(years)
	entities = sorted(entities)

	print("Calculating diffs...")
	sys.stdout.flush()

	diffs = []
	for prev_year in range(min(years),2020):
		for entity_type,entity_id in entities:
			prev_count = counts[ (prev_year,entity_type,entity_id) ]
			next_count = counts[ (prev_year+1,entity_type,entity_id) ]
			diff = next_count - prev_count
			mapping_key = "%s|%s" % (entity_type, entity_id)
			normalized = mapping[ mapping_key ] if mapping_key in mapping else 'Unknown'
			diffs.append( ( diff, prev_count, next_count, prev_year, entity_type, entity_id, normalized) )

	diffs = sorted(diffs, reverse=True)

	print("Saving...")
	sys.stdout.flush()

	with open(args.outFile,'w') as f:
		for diff_data in diffs[:10000]:
			f.write( "\t".join(map(str,diff_data)) + "\n" )

	print("Done")
	sys.stdout.flush()

