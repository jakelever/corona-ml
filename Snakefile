
rule:
	input: "data/autoannotations.json", "data/terms_drugs.json", "data/terms_geonames.json"

rule:
	output: "data/terms_drugs.json"
	shell: "python getDrugsFromWikidata.py --outJSON data/terms_drugs.json"
	
rule:
	output: "data/terms_geonames.json"
	shell: "python getGeonamesFromWikidata.py --outJSON data/terms_geonames.json"

rule:
	input: "data/alldocuments.json"
	output: "data/alldocuments.parsed.pickle"
	shell: "python parseDocuments.py --inJSON {input} --outPickle {output}"

rule:
	input: 
		json="data/alldocuments.json",
		parsed="data/alldocuments.parsed.pickle",
		drugs="data/terms_drugs.json",
		geonames="data/terms_geonames.json"
	output: "data/alldocuments.ner.json"
	shell: "python doNER.py --inJSON {input.json} --drugs {input.drugs} --geonames {input.geonames} --inParsed {input.parsed} --outJSON {output}"

rule:
	input: "data/alldocuments.ner.json",
	output: "data/alldocuments.withannotations.json"
	shell: "python integrateAnnotationsAndClean.py --inJSON {input} --outJSON {output}"

rule:
	input: "data/alldocuments.withannotations.json",
	output: "data/alldocuments.pubtype.json"
	shell: "python doPubType.py --inJSON {input} --outJSON {output}"

rule:
	input: "data/alldocuments.pubtype.json",
	output: "data/alldocuments.topics.json"
	shell: "python doTopics.py --inJSON {input} --outJSON {output}"
	
rule:
	input: "data/alldocuments.topics.json",
	output: "data/alldocuments.clinicaltrials.json"
	shell: "python doClinicalTrials.py --inJSON {input} --outJSON {output}"

rule:
	input: "data/alldocuments.clinicaltrials.json",
	output: "data/autoannotations.json"
	shell: "python createAutoAnnotations.py --inJSON {input} --outJSON {output}"