import json
import pickle
import os
import sys
from collections import defaultdict,Counter

class DocumentClassifier():
	def __init__(self, params):
		self.params = params
		self.fitted = False

	def fit(self,train_docs,train_targets,labels):
		assert self.fitted == False

		if self.params['clf'] == 'BERT':
			self.fit_bert(train_docs,train_targets,labels)
		else:
			self.fit_sklearn(train_docs,train_targets)

		self.fitted = True

	def predict(self,docs,return_scores=False):
		assert self.fitted == True

		if self.params['clf'] == 'BERT':
			return self.predict_bert(docs,return_scores)
		else:
			return self.predict_sklearn(docs,return_scores)
			
	def fit_bert(self, train_docs, train_targets, labels):
		import ktrain
		from ktrain import text
		from tensorflow import keras

		assert self.params['clf_model'] != ''

		t = text.Transformer(self.params['clf_model'],maxlen=500,class_names=labels)
		
		train_texts = [ d['title'] + "\n" + d['abstract'] for d in train_docs ]
		
		trn = t.preprocess_train(train_texts, train_targets)

		model = t.get_classifier()
		learner = ktrain.get_learner(model, train_data=trn, batch_size=self.params['clf_batch_size'])

		learner.fit_onecycle(self.params['clf_learning_rate'], self.params['clf_epochs'])
		
		#self.t = t
		#self.learner = learner

		self.predictor = ktrain.get_predictor(learner.model, preproc=t)
		#predictor.save('predictor.thing')
		#print(dir(learner))
		#learner.model.save('test.model')

	def predict_bert(self, docs, return_scores=False):
		import ktrain
		from ktrain import text
		from tensorflow import keras
		
		#model = keras.models.load_model('test.model')

		#self.learner = ktrain.get_learner(model)
		
		#predictor = ktrain.get_predictor(self.learner.model, preproc=self.t)
		#predictor = ktrain.get_predictor(self.learner.model)
		#predictor = ktrain.load_predictor('predictor.thing')
		
		texts = [ d['title'] + "\n" + d['abstract'] for d in docs ]
		
		scores = self.predictor.predict_proba(texts)

		if return_scores:
			return scores
		else:
			predictions = scores > 0.5
			return predictions

	def fit_sklearn(self, train_docs, train_targets):
		from coronacode import DocumentVectorizer
		from sklearn.linear_model import LogisticRegression
		from sklearn.svm import LinearSVC
		from sklearn.ensemble import RandomForestClassifier
		from sklearn.decomposition import TruncatedSVD
		from sklearn.pipeline import Pipeline
		from sklearn.multiclass import OneVsRestClassifier
		
		pipeline_parts = []
		
		pipeline_parts.append(("vectorizer", DocumentVectorizer(features=self.params['vectorizer_features'])))
		
		if 'svd_components' in self.params and self.params['svd_components']:
			pipeline_parts.append(("dimreducer", TruncatedSVD(n_components=self.params['svd_components'],random_state=0)))

		if self.params['clf'] == "LogisticRegression":
			clf = LogisticRegression(class_weight='balanced',random_state=0,C=self.params['clf_C'])
		elif self.params['clf'] == "LinearSVC":
			clf = LinearSVC(class_weight='balanced',random_state=0,C=self.params['clf_C'])
		elif self.params['clf'] == "RandomForestClassifier":
			clf = RandomForestClassifier(class_weight='balanced',random_state=0,n_estimators=self.params['clf_n_estimators'])

		if train_targets.shape[1] > 1:
			clf = OneVsRestClassifier(clf)
			
		pipeline_parts.append(("classifier", clf))

		self.pipeline = Pipeline(pipeline_parts)
		
		self.pipeline.fit(train_docs, train_targets)
		

	def predict_sklearn(self, docs, return_scores=False):
		if return_scores:
			scores = self.pipeline.predict_proba(docs)[:,1]
			return scores
		else:
			predictions = self.pipeline.predict(docs)
			return predictions

	def load(path):
		assert os.path.isdir(path), "Path must be a directory to load"

		params_path = os.path.join(path, 'params.json')

		with open(params_path,'r') as f:
			params = json.load(f)

		clf = DocumentClassifier(params)

		if params['clf'] == 'BERT':
			import ktrain
			predictor_path = os.path.join(path, 'predictor')
			clf.predictor = ktrain.load_predictor(predictor_path)
		else:
			pipeline_path = os.path.join(path, 'pipeline.pickle')
			with open(pipeline_path,'rb') as f:
				clf.pipeline = pickle.load(f)

		clf.fitted = True

		return clf

	def save(self, path):
		assert not (os.path.exists(path)), "%s already exists" % path
		assert self.fitted == True

		params_path = os.path.join(path, 'params.json')

		os.makedirs(path)
		with open(params_path,'w') as f:
			json.dump(self.params,f,indent=2,sort_keys=True)

		if self.params['clf'] == 'BERT':
			predictor_path = os.path.join(path, 'predictor')
			self.predictor.save(predictor_path)
		else:
			pipeline_path = os.path.join(path, 'pipeline.pickle')
			with open(pipeline_path,'wb') as f:
				pickle.dump(self.pipeline,f)

