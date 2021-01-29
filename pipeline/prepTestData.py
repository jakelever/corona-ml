import argparse
import json

with open('../pipeline/data/alldocuments.json') as f:
	documents = json.load(f)

#completed = documents[:10]
#incomplete = documents[:5]

#fields_to_remove = ['annotations','categories','entities','ids_from_merged_documents']
#for d in incomplete:
#	for f in fields_to_remove:
#		if f in d:
#			del d[f]

dois = ["10..5152/eurasianjmed.2020.010620","10.26434/chemrxiv.11860011.v2","10.1101/2020.07.01.20139857","10.1016/j.frl.2020.101682","10.1101/2020.07.05.20140467","10.1101/2020.06.08.20121541"]
cord_uids = ["joasxqb2","hdxjb2fn"]

subset = [ d for d in documents if d['doi'] in dois or d['cord_uid'] in cord_uids ]

with open('data/alldocuments.json','w') as f:
	json.dump(subset,f,indent=2,sort_keys=True)
#with open('data/coronacentral.json.prev','w') as f:
#	json.dump(incomplete,f,indent=2,sort_keys=True)

print("Saved %d documents" % len(subset))

