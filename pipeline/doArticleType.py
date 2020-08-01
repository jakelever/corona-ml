import argparse
import pickle
import json
from collections import defaultdict,Counter

from utils import DocumentVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import Pipeline

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Annotate documents with publication type (e.g. research article, review, news, etc)')
	parser.add_argument('--inJSON',required=True,type=str,help='Filename of JSON documents')
	parser.add_argument('--outJSON',required=True,type=str,help='Output JSON with entities')
	args = parser.parse_args()
	
	print("Loading documents...")
	
	with open(args.inJSON) as f:
		documents = json.load(f)
	
	#articleTypes = Counter( at for d in documents for at in d['web_articletypes'] )
	#articleTypes = [ (count,at) for at,count in articleTypes.items() ]
	#for count,at in sorted(articleTypes,reverse=True):
	#	if count > 10:
	#		print("%d\t%s" % (count,at))
	
	web_article_groups = {}
	web_article_groups['Research'] = "research-article,research,research letter,original research".split(',')
	web_article_groups['Comment/Editorial'] = "editorial,editorialnotes,commentary,viewpoint,comments & opinion,comment,perspective,article commentary,reply,editorials,correspondence response,perspectives,opinion piece,n-perspective,letter to the editor,letters to the editor,editorial/personal viewpoint,guest editorial,ce - letter to the editor,world view,current opinion,rapid response opinion,commentaries,invited commentary,article-commentary".split(',')
	web_article_groups['Review'] = "review article,reviewpaper,review,review-article,reviews,short review,summary review".split(',')
	web_article_groups['Meta-analysis'] = "meta-analysis".split(',')
	web_article_groups['News'] = "news".split(',')
	web_article_groups['Erratum'] = "erratum,correction".split(',')
	web_article_groups['Book chapter'] = "chapter".split(',')
	web_article_groups['Case Reports'] = "case report,case-report,clinical case report".split(',')
	
	selected_annotations = ['Review','Updates','Comment/Editorial','Meta-analysis','News','NotRelevant','Research','Book chapter','Erratum','Case Reports']
	
	#updates_journals = set(['MMWR. Morbidity and mortality weekly report','MMWR Morb Mortal Wkly Rep'])
	
	assert any( 'pub_type' in d for d in documents )
	
	for d in documents:
		confident_article_type = None
		
		annotated_articletypes = [ a for a in selected_annotations if a in d['annotations'] ]
		if 'NotRelevant' in annotated_articletypes:
			annotated_articletypes = ['NotRelevant']
		assert len(annotated_articletypes) <= 1, "Document has %s" % (str(annotated_articletypes))
		if len(d['annotations']) > 0 and len(annotated_articletypes) == 0:
			annotated_articletypes = ['Research']
		if 'Skip' in d['annotations'] or 'Maybe' in d['annotations']:
			annotated_articletypes = []
			
		mesh_pubtypes = d['pub_type'] if 'pub_type' in d else []
		
		types_from_webdata = [ group for group,names in web_article_groups.items() if any ( at in names for at in d['web_articletypes'] ) ]
		
		
		#if d['journal'] in updates_journals:
		#	predicted_articletype = 'Updates'
		
		if len(annotated_articletypes) == 1:
			confident_article_type = annotated_articletypes[0]
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
			confident_article_type = 'Case Reports'
		elif 'Research' in types_from_webdata or any('Clinical Trial' in pt for pt in mesh_pubtypes):
			confident_article_type = 'Research'
			
		if confident_article_type:
			d['article_type'] = confident_article_type
	
	training_data = [ d for d in documents if 'article_type' in d ]
	
	print("Got %d documents (of %d) with confident article types" % (len(training_data),len(documents)))
	
	unannotated = [ d for d in documents if not 'article_type' in d]
		
	print("Removing book chapters and erratum from training")
	training_data = [ d for d in training_data if not d['article_type'] in ['Book chapter','Erratum'] ]
		
	print("Vectorizing...")
	y = [ d['article_type'] for d in training_data ]
	
	pipeline = Pipeline([
		("vectorizer", DocumentVectorizer(features=['titleabstract'])),
		("classifier", LogisticRegression(class_weight='balanced',random_state=0))
	])
	
	print("Training...")
	pipeline.fit(training_data,y)
	
	probs = pipeline.predict_proba(documents)
	
	class_to_column = { c:i for i,c in enumerate(pipeline.classes_) }

	print("Classes:", pipeline.classes_)
	
	for i,d in enumerate(documents):
		if 'article_type' in d:
			continue
			
		reference_count = int(d['reference_count']) if 'reference_count' in d and d['reference_count'] else 0
			
		mesh_pubtypes = d['pub_type'] if 'pub_type' in d else []
		if 'Review' in mesh_pubtypes: # If it's tagged as a Review, it's definitely not research or news, but could be more than Review
			probs[i,class_to_column['Research']] = -1
			probs[i,class_to_column['News']] = -1
		elif reference_count > 50: # If it has a lot of references, it's either a review or a meta-analysis
			for j,c in enumerate(pipeline.classes_):
				if c != 'Review' and c != 'Meta-analysis':
					probs[i,j] = -1
					
		max_index = probs[i,:].argmax()
		score = probs[i,max_index]
		if score > 0.6:
			predicted_articletype = pipeline.classes_[max_index]
		else:
			predicted_articletype = 'Research'
		
		d['article_type'] = predicted_articletype
			
	print(Counter( d['article_type'] for d in documents))
	
	print("Cleaning up...")
	for d in documents:
		del d['web_articletypes']
			
	print("Saving JSON file...")
	with open(args.outJSON,'w') as f:
		json.dump(documents,f,indent=2,sort_keys=True)