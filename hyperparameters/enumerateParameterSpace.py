import itertools
import argparse

from collections import defaultdict
from collections.abc import Iterable

import numpy as np
import json

def unroll_search_space(search_space):
	space_unrolled = {}
	for name, arg_space in search_space.items():
		unrolled = []
		for obj_and_param_options in arg_space:
			if obj_and_param_options is None:
				unrolled.append(None)
				continue

			obj_and_param_options = { k:(v if k!='obj' and isinstance(v, Iterable) and not isinstance(v, str) else [v]) for k,v in obj_and_param_options.items() }
			params = [ dict(zip(obj_and_param_options.keys(),choice)) for choice in itertools.product(*obj_and_param_options.values()) ]
			unrolled += params
		space_unrolled[name] = unrolled

	complete_unroll = [ dict(zip(space_unrolled.keys(),choice)) for choice in itertools.product(*space_unrolled.values()) ]
	
	return complete_unroll

#print(len(complete_unroll))
def search_parameter_space(X, y, parameter_space, scoring="f1"):
	best_score,best_params = -999999,None
	complete_unroll = unroll_search_space(parameter_space)
	for i,params in enumerate(complete_unroll):
		pipeline = custom_pipeline(**params)
			
		results = cross_validate(pipeline, X, y, scoring=scoring, error_score='raise')
		avg_score = results['test_score'].mean()
		if avg_score > best_score:
			best_score = avg_score
			best_params = params
		
		#if True: #(i%100) == 0:
		print("%d/%d: best=%.3f score=%s %s" % (i+1,len(complete_unroll),best_score,avg_score,params))
			
		#break
		
	best_pipeline = custom_pipeline(**best_params)
		
	print("%d/%d: best_score=%.3f" % (len(complete_unroll),len(complete_unroll),best_score))
	return best_score,best_pipeline,best_params
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Enumerate all hyperparameters to try')
	parser.add_argument('--outSpace',required=True,type=str,help='Output JSON of all parameter options')
	args = parser.parse_args()
	
	vectorizer_features = ['title','abstract','titleabstract','journal']
	vectorizer_feature_search = [ list(choice)  for i in range(len(vectorizer_features)) for choice in itertools.combinations(vectorizer_features,i+1) ]

	classic_parameter_space = { #vectorizer_feature_search
		"vectorizer": [ {'obj':'DocumentVectorizer','features': vectorizer_feature_search } ],
		"dimreducer": [ None, {'obj':'TruncatedSVD','n_components': [5, 15, 30, 45, 64, 96, 128]} ],
		"classifier": [ 
			{'obj':'LogisticRegression','class_weight':'balanced', 'max_iter':10000, 'tol':0.1,'C':np.logspace(-4, 4, 4)},
			#{'obj':LinearSVC(),'class_weight':'balanced','random_state':1,'max_iter':10000,'C':np.logspace(-4, 4, 4)},
			#{'obj':RandomForestClassifier(),'class_weight':'balanced','n_estimators':[int(x) for x in np.linspace(start = 200, stop = 2000, num = 10)]}
			
		]
	}
	
	bert_parameter_space = {
		"classifier": [
			{"obj":'BertClassifier',
			"HUGGING_FACE_MODEL":['monologg/biobert_v1.1_pubmed','bert-base-uncased'],
			"MAX_LEN":[256,512],
			"batch_size":[32,64], 
			"epochs":[4],
			"features": [["title"],["title","abstract"]]
		}
		]
	}
	
	class_unroll = unroll_search_space(classic_parameter_space)
	bert_unroll = unroll_search_space(bert_parameter_space)
	
	complete_unroll = class_unroll + bert_unroll
	
	with open(args.outSpace,'w') as f:
		json.dump(complete_unroll,f,indent=2,sort_keys=True)
		
	print("Saved %d hyperparameter sets" % len(complete_unroll))