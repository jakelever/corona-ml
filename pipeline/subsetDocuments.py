import argparse
import json

def main():
	parser = argparse.ArgumentParser('Extract just a few documents for a test case')
	parser.add_argument('--inJSON',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--outJSON',required=True,type=str,help='JSON file with fewer documents')
	parser.add_argument('--num',required=False,type=int,default=10,help='Number of documents to select')
	args = parser.parse_args()

	print("Loading...")
	with open(args.inJSON) as f:
		documents = json.load(f)

	documents = documents[:args.num]
			
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)

if __name__ == '__main__':
	main()

