import argparse
import json
from collections import Counter,defaultdict
import re
import gzip

def infer_article_type_from_webdata(documents):
	articletype_fields = ['DC.Subject', 'DC.Type.articleType', 'DC.subject', 'WT.cg_s', 'WT.z_cg_type', 'WT.z_primary_atype', 'article:section', 'articleType', 'category', 'citation_article_type', 'citation_categories', 'citation_keywords', 'citation_section', 'dc.Type', 'dc.type', 'prism.section', 'wkhealth_toc_section', 'wkhealth_toc_sub_section','article-header__journal','primary-heading']
	
	for d in documents:
		document_webmetadata = defaultdict(list,d['webmetadata'])
		
		wm_articletypes = sum([ document_webmetadata[f] for f in articletype_fields ], [])
		wm_articletypes = sorted(set( at.strip().lower() for at in wm_articletypes if len(at) < 50 ))
		
		d['web_articletypes'] = wm_articletypes
		
	web_article_groups = {}
	web_article_groups['Research'] = "research-article,research,research letter,original research".split(',')
	web_article_groups['Comment/Editorial'] = "editorial,editorialnotes,commentary,viewpoint,comments & opinion,comment,perspective,article commentary,reply,editorials,correspondence response,perspectives,opinion piece,n-perspective,letter to the editor,letters to the editor,editorial/personal viewpoint,guest editorial,ce - letter to the editor,world view,current opinion,rapid response opinion,commentaries,invited commentary,article-commentary".split(',')
	web_article_groups['Review'] = "review article,reviewpaper,review,review-article,reviews,short review,summary review".split(',')
	web_article_groups['Meta-analysis'] = "meta-analysis".split(',')
	web_article_groups['News'] = "news".split(',')
	web_article_groups['Erratum'] = "erratum,correction".split(',')
	web_article_groups['Retraction'] = "retraction".split(',')
	web_article_groups['Book chapter'] = "chapter".split(',')
	web_article_groups['Case Reports'] = "case report,case-report,clinical case report".split(',')
	
	web_article_groups_by_journal = defaultdict(dict)
	web_article_groups_by_journal['Science']['Comment/Editorial'] = [ 'letter' ]

	retraction_keywords = ['retraction','retracted','withdrawn']
	
	assert any( 'medline_pubtype' in d for d in documents )
	
	for d in documents:
		confident_article_type = None
		
		mesh_pubtypes = d['medline_pubtype'] if 'medline_pubtype' in d else []
		
		types_from_webdata = [ group for group,names in web_article_groups.items() if any ( at in names for at in d['web_articletypes'] ) ]
		types_from_webdata += [ group for group,names in web_article_groups_by_journal[d['journal']].items() if any ( at in names for at in d['web_articletypes'] ) ]
		
				
		if 'Retraction' in types_from_webdata or 'Retracted Publication' in mesh_pubtypes or 'Retraction of Publication' in mesh_pubtypes or any( d['title'].lower().startswith(rk) for rk in retraction_keywords ):
			confident_article_type = 'Retracted'
		elif 'Erratum' in types_from_webdata or 'Published Erratum' in mesh_pubtypes or d['title'].lower().startswith('erratum')  or d['title'].lower().startswith('correction'):
			confident_article_type = 'Erratum'
		elif 'News' in types_from_webdata or any (pt in mesh_pubtypes for pt in ['News','Newspaper Article'] ):
			confident_article_type = 'News'
		elif 'Comment/Editorial' in types_from_webdata or any (pt in mesh_pubtypes for pt in ['Editorial','Comment'] ):
			confident_article_type = 'Comment/Editorial'
		elif 'Book chapter' in types_from_webdata or d['title'].startswith('Chapter '):
			confident_article_type = 'Book chapter'
		elif 'Meta-analysis' in types_from_webdata or any (pt in mesh_pubtypes for pt in ['Systematic Review','Meta-Analysis'] ):
			confident_article_type = 'Meta-analysis'
		elif 'Review' in types_from_webdata:
			confident_article_type = 'Review'
		elif 'Case Reports' in types_from_webdata or 'Case Reports' in mesh_pubtypes:
			confident_article_type = 'Research'
		elif 'Research' in types_from_webdata or any('Clinical Trial' in pt for pt in mesh_pubtypes):
			confident_article_type = 'Research'
			
		d['inferred_article_type'] = confident_article_type

	print("Inferred article types:")
	print(Counter( d['inferred_article_type'] for d in documents ))

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text).strip()
	
def is_cjk(character):
	""""
	Checks whether character is CJK.

		>>> is_cjk(u'\u33fe')
		True
		>>> is_cjk(u'\uFE5F')
		False

	:param character: The character that needs to be checked.
	:type character: char
	:return: bool
	"""
	return any([start <= ord(character) <= end for start, end in 
				[(4352, 4607), (11904, 42191), (43072, 43135), (44032, 55215), 
				 (63744, 64255), (65072, 65103), (65381, 65500), 
				 (131072, 196607)]
				])

def is_cjk_string(text):
	return any(is_cjk(ch) for ch in text)

dashCharacters = ["-", "\u00ad", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2043", "\u2053"]
def cleanup_dashes(list_of_text):
	new_list = []
	for item in list_of_text:
		for dc in dashCharacters:
			item = item.replace(dc,'-')
		new_list.append(item)
	return new_list

def main():
	parser = argparse.ArgumentParser('Integrate in metadata from web scraping')
	parser.add_argument('--inJSON',required=True,type=str,help='Input JSON documents')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with added metadata')
	args = parser.parse_args()
	
	print("Loading documents...")
	with gzip.open(args.inJSON,'rt') as f:
		documents = json.load(f)
	
	journalFields = ['citation_journal_title', 'journal', 'journalName', 'journal_title', 'wkhealth_journal_title']
		
	for d in documents:
		if 'webmetadata' in d and d['webmetadata'] and d['webmetadata']['status_code'] == 200:
			m = d['webmetadata']['parsed']
		else:
			m = {}
				
		m = { k:cleanup_dashes(vals) if isinstance(vals,list) else vals for k,vals in m.items() }
				
		d['webmetadata'] = defaultdict(list,m)
		
	print("Normalizing journal names using web data...")
	
	journal_fields = ['citation_journal_title', 'journal_title', 'journal', 'journalName', 'wkhealth_journal_title']

	skip_journal_list = ['arxiv','medrxiv','biorxiv','chemrxiv']
	
	journal_mapping = defaultdict(list)
	for d in documents:
		if any(skip_journal in d['journal'].lower() for skip_journal in skip_journal_list):
			continue
		
		wm_journals = sum([ d['webmetadata'][f] for f in journal_fields ], [])
		wm_journals = [ j for j in wm_journals if not is_cjk_string(j) ]
		if len(d['journal']) > 3 and wm_journals:
			d['wm_journal'] = wm_journals[0]
			journal_mapping[d['journal'].lower()].append(wm_journals[0])

	journal_mapping = { j:Counter(names).most_common(1)[0][0] for j,names in journal_mapping.items() if names }

	for d in documents:
		if 'wm_journal' in d:
			d['journal'] = d['wm_journal']
			del d['wm_journal']
		elif d['journal'] and d['journal'].lower() in journal_mapping:
			d['journal'] = journal_mapping[d['journal'].lower()]
		
	print("Finding abstracts for documents without abstracts...")
	
	abstract_fields = ['Abstract', 'DC.Description.Abstract', 'DC.abstract', 'abstract', 'citation_abstract', 'eprints.abstract']

	added_abstract_count = 0
	for d in documents:
		if d['abstract'] == '':
			candidate_abstracts = sum([ d['webmetadata'][f] for f in abstract_fields ], [])
			candidate_abstracts = [ remove_html_tags(ca) for ca in candidate_abstracts ]
			candidate_abstracts = [ ca for ca in candidate_abstracts if not ca.startswith('//') ]
			candidate_abstracts = [ ca for ca in candidate_abstracts if len(ca) > 100 ]
			candidate_abstracts = [ ca for ca in candidate_abstracts if not is_cjk_string(ca) ]
			
			candidate_abstracts = sorted(set(candidate_abstracts), key=lambda x: len(x), reverse=True)
			if candidate_abstracts:
				d['abstract'] = candidate_abstracts[0]
				added_abstract_count += 1
				
	print("Added %d new abstracts using web data" % added_abstract_count)
	
	print("Inferring article types using web data...")	
	infer_article_type_from_webdata(documents)
	article_type_count = len( [ d for d in documents if 'inferred_article_type' in d ] )
	print("Inferred article types for %d documents" % article_type_count)
	
	print("Saving data...")
	with gzip.open(args.outJSON,'wt',encoding='utf8') as f:
		json.dump(documents,f)

if __name__ == '__main__':
	main()

