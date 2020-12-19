#!/bin/bash
set -ex

db=aws.json
#db=remote.json
#db=local.json

python createDB.py --db $db

python loadDocsCleverly.py --db $db --json ../pipeline/data/coronacentral.json

python loadAnnotations.py --db $db --type auto --json ../pipeline/data/autoannotations.json

# Load older Altmetric data
python loadAltmetricData.py --db $db --json ../pipeline/data/altmetric.json

python loadLocationCoordinates.py --db $db --json ../pipeline/data/terms_locations.json

python cleanupDB.py --db $db

