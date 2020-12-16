import json
import argparse

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Make the JSON nice and readable')
	parser.add_argument('--inJSON',required=True,type=str,help='Input JSON file')
	parser.add_argument('--outJSON',required=True,type=str,help='Output nicer JSON file')
	args = parser.parse_args()

	with open(args.inJSON) as f:
		data = json.load(f)

	with open(args.outJSON,'w') as f:
		json.dump(data,f,indent=2,sort_keys=True)

	print("Done")
