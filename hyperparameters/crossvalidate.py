import sys
sys.path.append("../pipeline")

import json
#import tensorflow as tf


from sklearn.model_selection import StratifiedKFold
from sklearn.model_selection import train_test_split, cross_validate
from sklearn.pipeline import make_pipeline

from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import TruncatedSVD
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier

import itertools
from collections import defaultdict
from collections.abc import Iterable

from scipy.special import softmax
import numpy as np
import time
import datetime
import random
import os
import shutil
import argparse
import sklearn.metrics
                
from utils import DocumentVectorizer

def getDevice():
	import torch
	# If there's a GPU available...
	if torch.cuda.is_available():	
		# Tell PyTorch to use the GPU.	
		device = torch.device("cuda")

		#print('There are %d GPU(s) available.' % torch.cuda.device_count())

		print('We will use the GPU:', torch.cuda.get_device_name(0))

		# If not...
	else:
		#print('No GPU available, using the CPU instead.')
		device = torch.device("cpu")
	
	#torch.cuda.empty_cache()
	#assert False
		
	return device
	

class BertClassifier:
	def __init__(self, HUGGING_FACE_MODEL=None, MAX_LEN=None, batch_size=None, epochs=None, features=None):

		self.tokenizer = None
		self.model = None
		
		#self.device = self.getDevice()
		self.defaults = {'HUGGING_FACE_MODEL':'monologg/biobert_v1.1_pubmed', "MAX_LEN":256, "batch_size":32, "epochs":4, "features":["title","abstract"]}
		
		self.set_params(HUGGING_FACE_MODEL, MAX_LEN, batch_size, epochs, features)
		
		self.device = getDevice()
				
		
		
	def set_params(self,HUGGING_FACE_MODEL=None, MAX_LEN=None, batch_size=None, epochs=None, features=None):
		self.HUGGING_FACE_MODEL = HUGGING_FACE_MODEL if HUGGING_FACE_MODEL else self.defaults['HUGGING_FACE_MODEL']
		self.MAX_LEN = MAX_LEN if MAX_LEN else self.defaults['MAX_LEN']
		self.batch_size = batch_size if batch_size else self.defaults['batch_size']
		self.epochs = epochs if epochs else self.defaults['epochs']
		self.features = features if features else self.defaults['features']
		
		
	def get_params(self, deep):
		params = {'HUGGING_FACE_MODEL':self.HUGGING_FACE_MODEL, "MAX_LEN":self.MAX_LEN, "batch_size":self.batch_size, "epochs":self.epochs, "features":self.features}
		return params
		
	
		
	def __del__(self):
		if self.tokenizer is not None:
			del self.tokenizer
			self.tokenizer = None
		if self.model is not None:
			del self.model
			self.model = None
		
		#torch.cuda.empty_cache()
		
	def fit(self, documents, y, *args):
		assert len(documents) == len(y)
		
		if self.tokenizer is not None:
			del self.tokenizer
			self.tokenizer = None
		if self.model is not None:
			del self.model
			self.model = None

		import torch
		from transformers import BertTokenizer
		from keras.preprocessing.sequence import pad_sequences
		from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
		from transformers import BertForSequenceClassification, AdamW, BertConfig
		from transformers import get_linear_schedule_with_warmup	
			
		#torch.cuda.empty_cache()
		#printGPUMemory()
			
		self.tokenizer = BertTokenizer.from_pretrained(self.HUGGING_FACE_MODEL, do_lower_case=True)

		print("Training...")
		
		#train_texts = [ d['title'] for d in documents ]
		train_texts = [ "\n".join( d[f] for f in self.features ) for d in documents ]
		
		train_encoded = [ self.tokenizer.encode(doc,add_special_tokens = True,max_length=self.MAX_LEN,truncation=True) for doc in train_texts ]
		
		train_padded = pad_sequences(train_encoded, maxlen=self.MAX_LEN, dtype="long", 
									value=0, truncating="post", padding="post")
									
		train_padded = torch.tensor(train_padded)

		train_masks = [ [int(token_id > 0) for token_id in doc] for doc in train_padded ]

		train_masks = torch.tensor(train_masks)
		
		train_labels = torch.tensor(y)

		# Create the DataLoader for our training set.
		train_data = TensorDataset(train_padded, train_masks, train_labels)
		train_sampler = RandomSampler(train_data)
		train_dataloader = DataLoader(train_data, sampler=train_sampler, batch_size=self.batch_size)
		
		model = BertForSequenceClassification.from_pretrained(
			self.HUGGING_FACE_MODEL, # Use the 12-layer BERT model, with an uncased vocab.
			num_labels = 2, # The number of output labels--2 for binary classification.
					# You can increase this for multi-class tasks.   
			output_attentions = False, # Whether the model returns attentions weights.
			output_hidden_states = False, # Whether the model returns all hidden-states.
		)
		
		model.cuda()
		
		# Note: AdamW is a class from the huggingface library (as opposed to pytorch) 
		# I believe the 'W' stands for 'Weight Decay fix"
		optimizer = AdamW(model.parameters(),
				  lr = 2e-5, # args.learning_rate - default is 5e-5, our notebook had 2e-5
				  eps = 1e-8 # args.adam_epsilon  - default is 1e-8.
				)



		# Total number of training steps is number of batches * number of epochs.
		total_steps = len(train_dataloader) * self.epochs

		# Create the learning rate scheduler.
		scheduler = get_linear_schedule_with_warmup(optimizer, 
								num_warmup_steps = 0, # Default value in run_glue.py
								num_training_steps = total_steps)




		# This training code is based on the `run_glue.py` script here:
		# https://github.com/huggingface/transformers/blob/5bfcd0485ece086ebcbed2d008813037968a9e58/examples/run_glue.py#L128


		# Set the seed value all over the place to make this reproducible.
		seed_val = 42

		random.seed(seed_val)
		np.random.seed(seed_val)
		torch.manual_seed(seed_val)
		torch.cuda.manual_seed_all(seed_val)

		# Store the average loss after each epoch so we can plot them.
		loss_values = []

		# For each epoch...
		for epoch_i in range(0, self.epochs):
		
			# ========================================
			#			   Training
			# ========================================

			# Perform one full pass over the training set.

			#print("")
			#print('======== Epoch {:} / {:} ========'.format(epoch_i + 1, self.epochs))
			#print('Training...')

			# Measure how long the training epoch takes.
			t0 = time.time()

			# Reset the total loss for this epoch.
			total_loss = 0

			# Put the model into training mode. Don't be mislead--the call to 
			# `train` just changes the *mode*, it doesn't *perform* the training.
			# `dropout` and `batchnorm` layers behave differently during training
			# vs. test (source: https://stackoverflow.com/questions/51433378/what-does-model-train-do-in-pytorch)
			model.train()

			# For each batch of training data...
			for step, batch in enumerate(train_dataloader):

				# Progress update every 40 batches.
				#if step % 40 == 0 and not step == 0:
					# Calculate elapsed time in minutes.
				#	elapsed = format_time(time.time() - t0)
		
					# Report progress.
				#	print('  Batch {:>5,}  of  {:>5,}.	Elapsed: {:}.'.format(step, len(train_dataloader), elapsed))

				# Unpack this training batch from our dataloader. 
				#
				# As we unpack the batch, we'll also copy each tensor to the GPU using the 
				# `to` method.
				#
				# `batch` contains three pytorch tensors:
				#   [0]: input ids 
				#   [1]: attention masks
				#   [2]: labels 
				b_input_ids = batch[0].to(self.device)
				b_input_mask = batch[1].to(self.device)
				b_labels = batch[2].to(self.device)

				# Always clear any previously calculated gradients before performing a
				# backward pass. PyTorch doesn't do this automatically because 
				# accumulating the gradients is "convenient while training RNNs". 
				# (source: https://stackoverflow.com/questions/48001598/why-do-we-need-to-call-zero-grad-in-pytorch)
				model.zero_grad()		

				# Perform a forward pass (evaluate the model on this training batch).
				# This will return the loss (rather than the model output) because we
				# have provided the `labels`.
				# The documentation for this `model` function is here: 
				# https://huggingface.co/transformers/v2.2.0/model_doc/bert.html#transformers.BertForSequenceClassification
				outputs = model(b_input_ids, 
					token_type_ids=None, 
					attention_mask=b_input_mask, 
					labels=b_labels)

				# The call to `model` always returns a tuple, so we need to pull the 
				# loss value out of the tuple.
				loss = outputs[0]

				# Accumulate the training loss over all of the batches so that we can
				# calculate the average loss at the end. `loss` is a Tensor containing a
				# single value; the `.item()` function just returns the Python value 
				# from the tensor.
				total_loss += loss.item()

				# Perform a backward pass to calculate the gradients.
				loss.backward()

				# Clip the norm of the gradients to 1.0.
				# This is to help prevent the "exploding gradients" problem.
				torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

				# Update parameters and take a step using the computed gradient.
				# The optimizer dictates the "update rule"--how the parameters are
				# modified based on their gradients, the learning rate, etc.
				optimizer.step()

				# Update the learning rate.
				scheduler.step()

			# Calculate the average loss over the training data.
			avg_train_loss = total_loss / len(train_dataloader)			

			# Store the loss value for plotting the learning curve.
			loss_values.append(avg_train_loss)
			
		self.model = model
		#print(dir(model))
		#assert False
		
	def predict(self, documents, *args):
		import torch
		from transformers import BertTokenizer
		from keras.preprocessing.sequence import pad_sequences
		from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
		from transformers import BertForSequenceClassification, AdamW, BertConfig
		from transformers import get_linear_schedule_with_warmup

		#texts = [ d['title'] for d in documents ]
		texts = [ "\n".join( d[f] for f in self.features ) for d in documents ]
		
		kaggle_encoded = [ self.tokenizer.encode(doc,add_special_tokens = True,max_length=self.MAX_LEN,truncation=True) for doc in texts ]

		kaggle_padded = pad_sequences(kaggle_encoded, maxlen=self.MAX_LEN, dtype="long", 
						value=0, truncating="post", padding="post")
		kaggle_padded = torch.tensor(kaggle_padded)

		kaggle_masks = [ [int(token_id > 0) for token_id in doc] for doc in kaggle_padded ]
		kaggle_masks = torch.tensor(kaggle_masks)

		model = self.model

		model.eval()
		model.cuda()

		kaggle_indices = torch.tensor(list(range(kaggle_padded.shape[0])))
		kaggle_data = TensorDataset(kaggle_padded, kaggle_masks, kaggle_indices)
		kaggle_sampler = SequentialSampler(kaggle_data)
		kaggle_dataloader = DataLoader(kaggle_data, sampler=kaggle_sampler, batch_size=self.batch_size)

		kaggle_predictions = {}

		# Evaluate data for one epoch
		for batch in kaggle_dataloader:

			input_ids, input_mask, input_indices = batch

			b_input_ids = input_ids.to(self.device)
			b_input_mask = input_mask.to(self.device)

			# Telling the model not to compute or store gradients, saving memory and
			# speeding up validation
			with torch.no_grad():		

				# Forward pass, calculate logit predictions.
				# This will return the logits rather than the loss because we have
				# not provided labels.
				# token_type_ids is the same as the "segment ids", which 
				# differentiates sentence 1 and 2 in 2-sentence tasks.
				# The documentation for this `model` function is here: 
				# https://huggingface.co/transformers/v2.2.0/model_doc/bert.html#transformers.BertForSequenceClassification
				outputs = model(b_input_ids, 
					token_type_ids=None, 
					attention_mask=b_input_mask)

			# Get the "logits" output by the model. The "logits" are the output
			# values prior to applying an activation function like the softmax.
			logits = outputs[0]

			# Move logits and labels to CPU
			logits = logits.detach().cpu().numpy()
			softmaxed = softmax(logits,axis=1)

			predictions = softmaxed[:,1].flatten().tolist()
			for i,(input_index,prediction) in enumerate(zip(input_indices,predictions)):
				kaggle_predictions[input_index.int().item()] = prediction
				
		assert len(kaggle_predictions) == len(documents)
		
		#print(kaggle_predictions)
		
		kaggle_predictions_list = [ kaggle_predictions[i] for i in range(len(documents)) ]
		
		predictions = [ 1 if p > 0.5 else 0 for p in kaggle_predictions_list ]
		
		return predictions
		

def split_into_obj_and_params(estimator_dict):
	assert isinstance(estimator_dict,dict), "Received object of type: %s" % type(estimator_dict)
	assert 'obj' in estimator_dict, "Couldn't find obj in %s" % str(estimator_dict)
	estimator_dict = dict(estimator_dict)
	obj = estimator_dict['obj']
	del estimator_dict['obj']
	params = estimator_dict
	return obj,params

def custom_pipeline(vectorizer=None, dimreducer=None, classifier=None):
	assert not classifier is None
	
	vectorizer_obj,dimreducer_obj,classifier_obj = None,None,None
	
	#pipe = Pipeline()
	components = []
	if vectorizer:
		vectorizer_type,vectorizer_args = split_into_obj_and_params(vectorizer)
		if vectorizer_type == 'DocumentVectorizer':
			vectorizer_obj = DocumentVectorizer()
		vectorizer_obj.set_params(**vectorizer_args)
		components.append(('vectorizer', vectorizer_obj))
	
	if dimreducer:
		dimreducer_type,dimreducer_args = split_into_obj_and_params(dimreducer)
		if dimreducer_type == 'TruncatedSVD':
			dimreducer_obj = TruncatedSVD()
		
		dimreducer_obj.set_params(**dimreducer_args)
		components.append(('dimreducer',dimreducer_obj))
		
	classifier_type,classifier_args = split_into_obj_and_params(classifier)
	if classifier_type == 'BertClassifier':
		classifier_obj = BertClassifier()
	elif classifier_type == 'LogisticRegression':
		classifier_obj = LogisticRegression()
	elif classifier_type == 'LinearSVC':
		classifier_obj = LinearSVC()
	elif classifier_type == 'RandomForestClassifier':
		classifier_obj = RandomForestClassifier()
	
	classifier_obj.set_params(**classifier_args)
	components.append(('classifier', classifier_obj))
	
	pipe = Pipeline(components)
	
	return pipe
	
		
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Train a document classifier')
	parser.add_argument('--documents',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--parameterSpace',required=True,type=str,help='JSON file with parameter space')
	parser.add_argument('--parameterIndex',required=True,type=int,help='Which parameter set to use')
	
	args = parser.parse_args()
	
	with open(args.documents) as f:
		documents = json.load(f)
		
	annotated = [ d for d in documents if d['annotations'] ]
	
	labels = [ 1 if 'Transmission' in d['annotations'] else 0 for d in annotated ]
	#labels = [ 1 if 'Viral Biology' in d['annotations'] or 'Host Biology' in d['annotations'] else 0 for d in annotated ]
	
	assert sum(labels) > 0 and sum(labels) < len(labels), "Got %d positive labels of %d" % (sum(labels),len(labels))
	
	with open(args.parameterSpace) as f:
		parameterSpace = json.load(f)
	
	assert args.parameterIndex >= 0 and args.parameterIndex < len(parameterSpace)
	chosenParameters = parameterSpace[args.parameterIndex]
	
	pipeline = custom_pipeline(**chosenParameters)
	
	cv_results = cross_validate(pipeline, annotated, labels, scoring=('f1',), cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=42))
	mean_f1 = cv_results['test_f1'].mean()
	print("F1\t%f" % mean_f1)
	print(chosenParameters)
	
