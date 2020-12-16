import argparse
import json

BLUEBERT = '/home/groups/rbaltman/jlever/bluebert/base_uncased_pubmedANDmimicIII/'

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Enumerate all parameters')
	parser.add_argument('--outFile',required=True,type=str,help='JSON output file')
	args = parser.parse_args()
	
	#vectorizer_feature_options = {'vectorizer_features':'titleabstract'}

	#vectorizer_features_options = [ ['title'], ['abstract'], ['titleabstract'], ['journal'], ['title','abstract'], ['abstract'] ]
	#vectorizer_features_options +=  [ ['title','journal'] , ['abstract','journal'], ['titleabstract','journal'], ['title','abstract','journal'], ['abstract','journal'] ]

	vectorizer_features_options = [ ['title','abstract','journal'] ]
	
	clf_options = []
	
	for clf in ['LogisticRegression','LinearSVC','BERT','RandomForestClassifier']:
		if clf == 'LogisticRegression' or clf == 'LinearSVC':
			for svd_components in [None,8,16,32,64,128]:
				for C in [0.1, 1, 10, 20]:
					for vectorizer_features in vectorizer_features_options:
						clf_options.append( { "clf":clf, "clf_C":C, "svd_components":svd_components, 'vectorizer_features':vectorizer_features } )
		elif clf == 'RandomForestClassifier':
			for svd_components in [None,8,16,32,64,128]:
				for n_estimators in [50,100,200]:
					for vectorizer_features in vectorizer_features_options:
						clf_options.append( { "clf":clf, "clf_n_estimators":n_estimators, "svd_components":svd_components, 'vectorizer_features':vectorizer_features } )
		elif clf == 'BERT':
			for epochs in [4,8,12,16,24,32,48,64,80,96]:
				#for learning_rate in [1e-5]:
				for learning_rate in [1e-3,5e-4,1e-4,5e-5,1e-5,5e-6]:
					for batch_size in [8]:
						for model in [BLUEBERT,'dmis-lab/biobert-v1.1','microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext','microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract','allenai/scibert_scivocab_uncased','allenai/scibert_scivocab_cased']:
							clf_options.append( { "clf":clf, "clf_epochs":epochs, "clf_learning_rate":learning_rate, 'clf_model':model, 'clf_batch_size':batch_size } )
			
	print("Saving %d options" % len(clf_options))
	with open(args.outFile,'w') as f:
		json.dump(clf_options,f,indent=2,sort_keys=True)
	
