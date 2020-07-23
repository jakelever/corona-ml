import argparse
from collections import defaultdict,OrderedDict
import json
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Tool to put coronavirus proteins into entity format')
	parser.add_argument('--viruses',type=str,required=True,help='JSON file with virus aliases')
	parser.add_argument('--outJSON',type=str,required=True,help='File to output entities')
	args = parser.parse_args()

	virus_aliases = {}
	with open(args.viruses) as f:
		virus_data = json.load(f)
		for wikidataID,v in virus_data.items():
			name = v['name']
			aliases = v['aliases'] + [name.lower()]
			aliases = sorted(set(aliases))
			virus_aliases[name] = aliases

	entities = {}
	print('Adding custom coronavirus proteins...')
	structural_proteins = ['envelope','spike','membrane']
	for virus in ['SARS-CoV-2','SARS-CoV','MERS-CoV']:
		for protein in structural_proteins:
			singleletter = protein[0].upper()
			
			aliases = []
			for alias in virus_aliases[virus]:
				aliases += [ '%s %s protein' % (alias,protein), '%s %s protein' % (alias,singleletter), '%s %s glycoprotein' % (alias,singleletter), '%s %s (%s) protein' % (alias,protein,singleletter), '%s %s glycoprotein' % (alias,protein), '%s %s (%s) glycoprotein' % (alias,protein,singleletter), '(%s) %s protein' % (alias,protein), '(%s) %s (%s) protein' % (alias,protein,singleletter), '(%s) %s glycoprotein' % (alias,protein) , '(%s) %s (%s) glycoprotein' % (alias,protein,singleletter) ]
			
			ambig_aliases = [ '%s protein' % protein, 'coronavirus %s protein' % protein ]
			
			short_name = '%s_%s' % (virus.replace('-','').lower(),protein.lower())
			long_name = '%s %s protein' % (virus,protein)
			entities[short_name] = {'name':long_name, 'type': 'gene_or_protein', 'associated_virus':virus, 'aliases':aliases, 'ambiguous_aliases': ambig_aliases}
		
	other_proteins = {}
	
	other_proteins['SARS-CoV'] = ['ORF1a','ORF1b','ORF2','ORF3','ORF3a','ORF3b','ORF4','ORF5','ORF6','ORF7a','ORF7b','ORF8','ORF8a','ORF8b','ORF9a','ORF9b'] + [ 'NSP%d' % num for num in range(1,17) ]
	other_proteins['SARS-CoV-2'] = ['ORF1ab','ORF3a','ORF6','ORF7a','ORF8','ORF10'] + [ 'NSP%d' % num for num in range(1,17) ]
	other_proteins['MERS-CoV'] = ['ORF2','ORF3','ORF4a','ORF4b','ORF5','ORF6','ORF7','ORF8a'] + [ 'NSP%d' % num for num in range(1,17) ]
	
	orfAliases = ['ORF-','ORF ','open reading frame ','open-reading frame ','open reading-frame ','open-reading-frame ' ]
	nspAliases = ['NSP-','NSP ','non structural protein ','non-structural protein ','non structural-protein ','non-structural-protein ' ]
	
	for virus,proteins in other_proteins.items():
		for protein in proteins:
		
			if len(protein) == 1:
				aliases = [ '%s %s protein' % (v,protein) for v in virus_aliases[virus] ]
				ambig_aliases = [ '%s protein' % protein ]
			else:
				aliases = [ template % (v,protein) for template in [ '%s %s', '%s %s protein' ] for v in virus_aliases[virus] ]
				ambig_aliases = [ '%s protein' % protein, protein ]
				
			# Allow a dash or space for ORF/NSP proteins (e.g. NSP-5 and NSP 5, not just NSP5)
			if protein.startswith('ORF'):
				aliases += [ a.replace('ORF',repl) for a in aliases for repl in orfAliases ]
				ambig_aliases += [ a.replace('ORF',repl) for a in ambig_aliases for repl in orfAliases ]
			if protein.startswith('NSP'):
				aliases += [ a.replace('NSP',repl) for a in aliases for repl in nspAliases ]
				ambig_aliases += [ a.replace('NSP',repl) for a in ambig_aliases for repl in nspAliases ]
				
			aliases = sorted(set(aliases))
			ambig_aliases = sorted(set(ambig_aliases))
				
			short_name = '%s_%s' % (virus.lower().replace('-',''),protein.lower())
			long_name = '%s %s protein' % (virus,protein)
			entities[short_name] = {'name':long_name, 'type': 'gene_or_protein', 'associated_virus':virus, 'aliases':aliases, 'ambiguous_aliases': ambig_aliases}
	
	entities['sarscov2_nsp5']['aliases'] += [ template % virus for template in ['%s 3CL(Pro)','%s 3CL Pro ','%s 3CLPro','%s 3C-like protease','%s main proteinase'] for virus in virus_aliases['SARS-CoV-2'] ]
	entities['sarscov2_nsp5']['ambiguous_aliases'] += ['3CL(Pro)','3CL Pro','3CLPro','3C-like protease']
	
	entities['sarscov_nsp5']['aliases'] += [ template % virus for template in ['%s 3CL(Pro)','%s 3CL Pro ','%s 3CLPro','%s 3C-like protease','%s main proteinase'] for virus in virus_aliases['SARS-CoV'] ]
	entities['sarscov_nsp5']['ambiguous_aliases'] += ['3CL(Pro)','3CL Pro','3CLPro','3C-like protease']
	
	print('Saving JSON file...')
	with open(args.outJSON,'w') as f:
		#entities_as_list = [ entities[entityID] for entityID in sorted(entities.keys()) ]
		json.dump(entities,f,indent=2,sort_keys=True)


