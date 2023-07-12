import argparse
import json

import re
import os

from intervaltree import IntervalTree
from collections import defaultdict
import gzip

aminoAcidInfo = [('ALA','A'),('ARG','R'),('ASN','N'),('ASP','D'),('CYS','C'),('GLU','E'),('GLN','Q'),('GLY','G'),('HIS','H'),('ILE','I'),('LEU','L'),('LYS','K'),('MET','M'),('PHE','F'),('PRO','P'),('SER','S'),('THR','T'),('TRP','W'),('TYR','Y'),('VAL','V'),('ALANINE','A'), ('CYSTEINE','C'), ('ASPARTICACID','D'), ('GLUTAMICACID','E'), ('PHENYLALANINE','F'), ('GLYCINE','G'), ('HISTIDINE','H'), ('ISOLEUCINE','I'), ('LYSINE','K'), ('LEUCINE','L'), ('METHIONINE','M'), ('ASPARAGINE','N'), ('PROLINE','P'), ('GLUTAMINE','Q'), ('ARGININE','R'), ('SERINE','S'), ('THREONINE','T'), ('VALINE','V'), ('TRYPTOPHAN','W'), ('TYROSINE','Y'),('STOP','X'),('TER','X')]
aminoAcidMap = { big:small for big,small in aminoAcidInfo }
for letter in 'ABCDEFGHIKLMNPQRSTVWYZX':
	aminoAcidMap[letter] = letter
aminoAcidMap['*'] = '*'

regexes = []
ignore_regexes = []

def prepareRegexes():
	
	examples = [
		
		('IGNORED',	'THR790MET791'),
		('IGNORED',	'THR790/MET/791'),
		('IGNORED',	'THR790 to MET 791'),
		('IGNORED',	'THR-790 to MET-791'),
		('IGNORED',	'THR790-to-MET-791'),
		('IGNORED',	'THR790->MET791'),
		('IGNORED',	'THR790-->MET791'),
		('IGNORED',	'THR790-MET-791'),
		('IGNORED',	'THR790----MET791'),
		('IGNORED',	'790THR----MET791'),
		('IGNORED',	'THR-790-MET-791'),
		('IGNORED',	'THR-790MET-791'),
		('IGNORED',	'THR-790 -> MET-791'),
		('IGNORED',	'THR-790 --> MET-791'),
		('IGNORED',	'THR(790)MET(791)'),
		
		('p.T790M',	'T790M'),
		('p.T790M',	'T790E/M'),
		('p.T790M',	'T790E/V/M'),
		('c.93G>A',	'G93A'),
		('c.93G>A',	'c.G93A'),
		('c.93G>A',	'c.93G>A'),
		('c.93G>A',	'c.93G/A'),
		('c.93G>A',	'93G>A'),
		('c.93G>A',	'G/A-93'),
		('c.93G>A',	'93G->A'),
		('c.93G>A',	'93G-->A'),
		('c.93G>A',	'G93->A'),
		('c.93G>A',	'G93-->A'),
		('c.93G>A',	'93G-A'),
		('c.93G>A',	'G modified A 93'),
		('c.93G>A',	'93G/A'),
		('c.93G>A',	'93,G/A'),
		('c.93G>A',	'(93) G/A'),
		('c.93G>A',	'93 (G/A)'),
		('c.93G>A',	'G to A substitution at nucleotide 93'),
		('c.93G>A',	'G to A substitution at position 93'),
		('c.93G>A',	'G to A at nucleotide 93'),
		('c.93G>A',	'G to A at position 93'),
		('c.93G>A',	'g+93G>A'),
		('c.93delG',	'c.93delG'),
		('c.93delG',	'c.93Gdel'),
		('c.93delG',	'93delG'),
		('c.93delG',	'93Gdel'),
		('c.93GGC>GAC',	'GGC93GAC'),
		('c.93_94del',	'c.93-94del'),
		('c.93_94del',	'c.93_94del'),
		('c.93_94del',	'93-94del'),
		('c.93_94del',	'93_94del'),
		('c.93dup',	'c.93dup'),
		('c.93_94dup',	'c.93-94dup'),
		('c.93_94dup',	'c.93_94dup'),
		('c.93_94dup',	'93-94dup'),
		('c.93_94dup',	'93_94dup'),
		('g.93G>A',	'g.93G>A'),
		('m.93G>A',	'm.93G>A'),
		('p.T790M',	'THR790MET'),
		('p.T790M',	'THR790/MET'),
		('p.T790M',	'THR790 to MET'),
		('p.T790M',	'THR-790 to MET'),
		('p.T790M',	'THR790-to-MET'),
		('p.T790M',	'THR790->MET'),
		('p.T790M',	'THR790-->MET'),
		('p.T790M',	'THR790-MET'),
		('p.T790M',	'THR790----MET'),
		('p.T790M',	'790THR----MET'),
		('p.T790M',	'THR-790-MET'),
		('p.T790M',	'THR-790MET'),
		('p.T790M',	'THR-790 -> MET'),
		('p.T790M',	'THR-790 --> MET'),
		('p.T790M',	'THR(790)MET'),
		('p.T790M',	'p.THR790MET'),
		('p.T790M',	'THR-to-MET substitution at position 790'),
		('p.T790M',	'THR 790 is replaced by MET'),
		('p.T790M',	'THR 790 mutated to MET'),
		('p.T790M',	'THR 790 was mutated to MET'),
		('p.T790M',	'THREONINE-to-METHIONINE mutation at residue 790'),
		('p.T790M',	'THREONINE-to-METHIONINE mutation at amino acid 790'),
		('p.T790M',	'THREONINE-to-METHIONINE mutation at amino acid position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE mutation at position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE mutation in position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE substitution at residue 790'),
		('p.T790M',	'THREONINE-to-METHIONINE substitution at amino acid 790'),
		('p.T790M',	'THREONINE-to-METHIONINE substitution at amino acid position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE substitution at position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE substitution in position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE alteration at residue 790'),
		('p.T790M',	'THREONINE-to-METHIONINE alteration at amino acid 790'),
		('p.T790M',	'THREONINE-to-METHIONINE alteration at amino acid position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE alteration at position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE alteration in position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE change at residue 790'),
		('p.T790M',	'THREONINE-to-METHIONINE change at amino acid 790'),
		('p.T790M',	'THREONINE-to-METHIONINE change at amino acid position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE change at position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE change in position 790'),
		('p.T790M',	'THREONINE-to-METHIONINE at residue 790'),
		('p.T790M',	'THREONINE-to-METHIONINE at amino acid 790'),
		('p.T790M',	'THREONINE to METHIONINE mutation at residue 790'),
		('p.T790M',	'THREONINE to METHIONINE mutation at amino acid 790'),
		('p.T790M',	'THREONINE to METHIONINE mutation at amino acid position 790'),
		('p.T790M',	'THREONINE to METHIONINE mutation at position 790'),
		('p.T790M',	'THREONINE to METHIONINE mutation in position 790'),
		('p.T790M',	'THREONINE to METHIONINE substitution at residue 790'),
		('p.T790M',	'THREONINE to METHIONINE substitution at amino acid 790'),
		('p.T790M',	'THREONINE to METHIONINE substitution at amino acid position 790'),
		('p.T790M',	'THREONINE to METHIONINE substitution at position 790'),
		('p.T790M',	'THREONINE to METHIONINE substitution in position 790'),
		('p.T790M',	'THREONINE to METHIONINE alteration at residue 790'),
		('p.T790M',	'THREONINE to METHIONINE alteration at amino acid 790'),
		('p.T790M',	'THREONINE to METHIONINE alteration at amino acid position 790'),
		('p.T790M',	'THREONINE to METHIONINE alteration at position 790'),
		('p.T790M',	'THREONINE to METHIONINE alteration in position 790'),
		('p.T790M',	'THREONINE to METHIONINE change at residue 790'),
		('p.T790M',	'THREONINE to METHIONINE change at amino acid 790'),
		('p.T790M',	'THREONINE to METHIONINE change at amino acid position 790'),
		('p.T790M',	'THREONINE to METHIONINE change at position 790'),
		('p.T790M',	'THREONINE to METHIONINE change in position 790'),
		('p.T790M',	'THREONINE to METHIONINE at residue 790'),
		('p.T790M',	'THREONINE to METHIONINE at amino acid 790'),
		('p.T790M',	'THREONINE by METHIONINE at position 790'),
		('p.T790M',	'THREONINE-790-METHIONINE'),
		('p.T790M',	'THREONINE-790 -> METHIONINE'),
		('p.T790M',	'THREONINE-790 --> METHIONINE'),
		('p.T790M',	'THREONINE 790 METHIONINE'),
		('p.T790M',	'THREONINE 790 changed to METHIONINE'),
		('p.T790M',	'THREONINE-790 METHIONINE'),
		('p.T790M',	'THREONINE 790-METHIONINE'),
		('p.T790M',	'THREONINE 790 to METHIONINE'),
		('p.T790M',	'THREONINE 790 by METHIONINE'),
		('p.T790M',	'790 THREONINE to METHIONINE'),
		('p.T790M',	'METHIONINE for THREONINE at amino acid 790'),
		('p.T790M',	'METHIONINE for THREONINE at position 790'),
		('p.T790M',	'METHIONINE for THREONINE 790'),
		('p.T790M',	'METHIONINE-for-THREONINE at position 790'),
		('p.T790M',	'METHIONINE for THREONINE substitution at position 790'),
		('p.T790M',	'METHIONINE-for-THREONINE substitution at position 790'),
		('p.T790M',	'METHIONINE for a THREONINE at position 790'),
		('p.T790M',	'METHIONINE for an THREONINE at position 790'),

		('p.T790M',	'p.T790M'),
		('p.T790M',	'p.(T790M)'),
		('p.T790M',	'790T>M'),
		('p.T790M',	'790T->M'),
		('p.T790M',	'790T-->M'),
		('p.T790M',	'T790->M'),
		('p.T790M',	'T790-->M'),
		('p.T790fsX',	'T790fs'),
		('p.T790fsX791','p.T790fsX791'),
		('p.T790fsX791','p.THR790fsx791'),
		('p.T790fsX791','THR790fsx791'),
		('p.790delT',	'THR790del'),
		('p.790delT',	'p.T790del'),
		('p.790delT',	'p.790delT'),
		('p.790delT',	'T790del'),
		('p.790delT',	'790delT'),
	]
	
	examples = sorted(examples, reverse=True, key=lambda x:len(x[1]))
	
	#examples = [('p.T790M',	'T790M')]
	
	for patternOut,patternIn in examples:
		
		#patternIn = re.sub('([A-Z])(\d)','\\1 \\2',patternIn)
		#patternIn = re.sub('(\d)([A-Z])','\\1 \\2',patternIn)
		patternIn = re.sub('([A-Z])([^A-Za-z0-9\ \/])','\\1 \\2',patternIn)
		patternIn = re.sub('([^A-Za-z0-9\ \/])([A-Z])','\\1 \\2',patternIn)
		#patternIn = re.sub('([a-z])(\d)','\\1 \\2',patternIn)
		#patternIn = re.sub('(\d)([a-z])','\\1 \\2',patternIn)
		patternIn = re.sub('([a-z])([^A-Za-z0-9\ \/])','\\1 \\2',patternIn)
		patternIn = re.sub('([^A-Za-z0-9\ \/])([a-z])','\\1 \\2',patternIn)
		#patternIn = re.sub('([a-z])([A-Z])','\\1 \\2',patternIn)
		#patternIn = re.sub('([A-Z])([a-z])','\\1 \\2',patternIn)
		patternIn = re.sub('(\d)([^A-Za-z0-9\ \/])','\\1 \\2',patternIn)
		patternIn = re.sub('([^A-Za-z0-9\ \/])(\d)','\\1 \\2',patternIn)
		patternIn = re.sub('\ +',' ',patternIn)
		
		#regex = "%s" % re.escape(patternIn.replace(' ',''))
		regex = re.escape(patternIn)

		mapping = [
			('THREONINE','(?P<from>Alanine|Cysteine|AsparticAcid|GlutamicAcid|Phenylalanine|Glycine|Histidine|Isoleucine|Lysine|Leucine|Methionine|Asparagine|Proline|Glutamine|Arginine|Serine|Threonine|Valine|Tryptophan|Tyrosine)'),
			('METHIONINE','(?P<to1>Alanine|Cysteine|AsparticAcid|GlutamicAcid|Phenylalanine|Glycine|Histidine|Isoleucine|Lysine|Leucine|Methionine|Asparagine|Proline|Glutamine|Arginine|Serine|Threonine|Valine|Tryptophan|Tyrosine)'),
			('THR','(?P<from>Ala|Arg|Asn|Asp|Cys|Glu|Gln|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val)'),
			('MET','(?P<to1>Ala|Arg|Asn|Asp|Cys|Glu|Gln|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val|X|\*|Ter|Stop)'),
			('790','(?P<num>[1-9][0-9]*)'),
			('791','(?P<num2>[1-9][0-9]*)'),
			('T','(?P<from>[ABCDEFGHIKLMNPQRSTVWYZ])'),
			('M','(?P<to1>([ABCDEFGHIKLMNPQRSTVWYZX\*]|stop))'),
			('E','(?P<to2>[ABCDEFGHIKLMNPQRSTVWYZX\*])'),
			('V','(?P<to3>[ABCDEFGHIKLMNPQRSTVWYZX\*])'),
			('GGC','(?P<from>[acgt]+)'),
			('GAC','(?P<to1>[acgt]+)'),
			('G','(?P<from>[acgt])'),
			('A','(?P<to1>[acgt])'),
			('C','(?P<to2>[acgt])'),
			('93','(?P<num>[\+\-]?[1-9][0-9\-\+]*)'),
			('94','(?P<num2>[\+\-]?[1-9][0-9\-]*)')
			]

		unique = {}
		for mapFrom,mapTo in mapping:
			unique[mapFrom] = "!!!%04d" % len(unique)
			regex = regex.replace(mapFrom, unique[mapFrom])
		for mapFrom,mapTo in mapping:
			regex = regex.replace(unique[mapFrom], mapTo)
			
		regex = regex.replace('\\ ','\s*')
		
		#print(regex)
			
		#compiled = re.compile(regex, re.IGNORECASE)
		compiled = re.compile(r'\b%s\b' % regex, re.IGNORECASE)
		
		#if patternOut == 'IGNORED':
		#	ignore_regexes.append(compiled)
		#else:
		regexes.append((compiled,patternIn,patternOut))

prepareRegexes()


def findGeneticVariation(text,stopwords):
	
	variants = {}
	
	
	for regex,patternIn,patternOut in regexes:
		toerase = []
		
		for match in re.finditer(regex, text):
			
			start = match.start()
			end = match.end()
			variant_text = match.group()
			
			
			#results[0].start(),results[0].end(), results[0].group()
			
			if match.group().lower() in stopwords:
				continue
			
			d = { key:value.upper() for key,value in match.groupdict().items() }
			if 'num' in d:
				d['num'] = d['num'].rstrip('-+')
				

			normalized = None
			if patternOut == 'c.G>A':
				normalized = "c.%s>%s" % (d['from'],d['to1'])
			elif patternOut == 'c.93G>A':
				normalized = "c.%s%s>%s" % (d['num'],d['from'],d['to1'])
			elif patternOut == 'c.93delG':
				normalized = "c.%sdel%s" % (d['num'],d['from'])
			elif patternOut == 'c.GGC>GAC':
				normalized = "c.%s>%s" % (d['from'],d['to1'])
			elif patternOut == 'c.93GGC>GAC':
				normalized = "c.%s%s>%s" % (d['num'],d['from'],d['to1'])
			elif patternOut == 'c.93G>A,C':
				normalized = "c.%s%s>%s,%s" % (d['num'],d['from'],d['to1'],d['to2'])
			elif patternOut == 'c.93_94del':
				normalized = "c.%s_%sdel" % (d['num'],d['num2'])
			elif patternOut == 'c.93_94dup':
				normalized = "c.%s_%sdup" % (d['num'],d['num2'])
			elif patternOut == 'c.93dup':
				normalized = "c.%sdup" % d['num']
			elif patternOut == 'g.93G>A':
				normalized = "g.%s%s>%s" % (d['num'],d['from'],d['to1'])
			elif patternOut == 'm.93G>A':
				normalized = "m.%s%s>%s" % (d['num'],d['from'],d['to1'])
			elif patternOut == 'p.TM':
				normalized = "p.%s%s" % (aminoAcidMap[d['from']],aminoAcidMap[d['to1']])
			elif patternOut == 'p.T790M':
				normalized = "p.%s%s%s" % (aminoAcidMap[d['from']],d['num'],aminoAcidMap[d['to1']])
			elif patternOut == 'p.T790fsX':
				normalized = "p.%s%sfsX" % (aminoAcidMap[d['from']],d['num'])
			elif patternOut == 'p.T790fsX791':
				normalized = "p.%s%sfsX%s" % (aminoAcidMap[d['from']],d['num'],d['num2'])
			elif patternOut == 'p.790delT':
				normalized = "p.%sdel%s" % (d['num'],aminoAcidMap[d['from']])
				
			if patternIn in ['T790E/M','T790E/V/M']:
				start = end - 2
				variant_text = variant_text[-2:]
				
			if normalized:
				variant = {'text':variant_text, 'start':start, 'end':end,'normalized':normalized, 'parts':d}
				variants[(variant['start'],variant['end'])] = variant
			
			toerase.append( (start,end) )
			
		#if toerase:
		#	print(patternIn, patternOut, variants, text)
		#	print()
			 
		allowOverlap = patternIn in ['T790M','T790E/M','T790E/V/M']
		if not allowOverlap:
			for start,end in toerase:
				text = text[:start] + " " * (end-start) + text[end:]

	return list(variants.values())

rs_regex = re.compile('rs\d\d+')
strain_regexes = [ re.compile(r'\b[ABCP]\.\d\d?(\.\d+)*\.?\b'),
                   re.compile(r'\b(\w+\/)?\d+Y\.V\d+\b'),
                   re.compile(r'\b((variant of concern|VOC|\(voc\))[-\s]*)+(?P<name>\d+/\d+)\b', flags=re.IGNORECASE) ]	

normalized_strains = {}
normalized_strains['B.1.1.7'] = 'B.1.1.7 (UK)'
normalized_strains['501Y.V1'] = 'B.1.1.7 (UK)'
normalized_strains['20I/501Y.V1'] = 'B.1.1.7 (UK)'
normalized_strains['20B/501Y.V1'] = 'B.1.1.7 (UK)'
normalized_strains['202012/01'] = 'B.1.1.7 (UK)'
normalized_strains['B.1.351'] = 'B.1.351 (South Africa)'
normalized_strains['501Y.V2'] = 'B.1.351 (South Africa)'
normalized_strains['20H/501Y.V2'] = 'B.1.351 (South Africa)'
normalized_strains['P.1'] = 'P.1 (Brazil)'

def processDoc(d,stopwords):
	d['variants'] = []
	d['viral_lineages'] = []
	for section in ['title','abstract']:
	
		variants = findGeneticVariation(d[section],stopwords)
		
		variants_as_entities = []
		for v in variants:
			entity = {'start':v['start'],'end':v['end'],'section':section,'id':v['normalized'],'type':'Genetic Variation','text':v['text'],'normalized':v['normalized']}
			variants_as_entities.append(entity)
			
		for match in re.finditer(rs_regex, d[section]):
			entity = {'start':match.start(),'end':match.end(),'section':section,'id':match.group(),'type':'Genetic Variation','text':match.group(),'normalized':match.group()}
			variants_as_entities.append(entity)
		d['variants'] += variants_as_entities

		strains_as_entities = []
		for strain_regex in strain_regexes:
			for match in re.finditer(strain_regex, d[section]):
				normalized = match.groupdict()['name'] if 'name' in match.groupdict() else match.group()
				if normalized in normalized_strains:
					normalized = normalized_strains[normalized]

				entity = {'start':match.start(),'end':match.end(),'section':section,'id':normalized,'type':'Viral Lineage','text':match.group(),'normalized':normalized}
				strains_as_entities.append(entity)
		d['viral_lineages'] += strains_as_entities
				

def main():
	parser = argparse.ArgumentParser(description='Extract genetic variation from documents and save as variants')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--prevJSON',type=str,required=False,help='Optional previously processed output (to save time)')
	parser.add_argument('--stopwords',type=str,required=True,help='Stopwords for variants')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with variants')
	args = parser.parse_args()
	
	variants_map = {}
	viral_lineages_map = {}
	if args.prevJSON and os.path.isfile(args.prevJSON):
		with gzip.open(args.prevJSON,'rt') as f:
			prev_documents = json.load(f)

		for d in prev_documents:
			key = (d['title'],d['abstract'])
			variants_map[key] = d['variants']
			viral_lineages_map[key] = d['viral_lineages']

	with gzip.open(args.inJSON,'rt') as f:
		documents = json.load(f)

	needs_doing = []
	already_done = []
	for d in documents:
		key = (d['title'],d['abstract'])
		if key in variants_map and key in viral_lineages_map:
			d['variants'] = variants_map[key]
			d['viral_lineages'] = viral_lineages_map[key]
			already_done.append(d)
		else:
			needs_doing.append(d)
		
	print("%d documents previously processed" % len(already_done))
	print("%d documents to be processed" % len(needs_doing))
	print()

	with open(args.stopwords) as f:
		stopwords = set( [ line.strip().lower() for line in f ] )
		
	print("Finding genetic variation...")
	
	for d in needs_doing:
		processDoc(d,stopwords)
			
	#print("Checking for no overlap...")
	#for d in documents:
	#	identifiers = [ d[idfield] for idfield in ['doi','pubmed_id','cord_uid','url'] ]
	
	#	trees = defaultdict(IntervalTree)
	#	for e in d['entities']:
	#		tree = trees[e['section']]
	#		assert len(tree[e['start']:e['end']]) == 0, "Found overlap in entities for document: %s" % str(identifiers)
	#		tree[e['start']:e['end']] = True

	output_documents = already_done + needs_doing
			
	assert len(documents) == len(output_documents)
	assert all('variants' in d for d in output_documents), "Expected documents to all have variants extracted"
			
	print("Saving data...")
	with gzip.open(args.outJSON,'wt',encoding='utf8') as f:
		json.dump(output_documents,f,indent=2,sort_keys=True)
	
if __name__ == '__main__':
	main()

