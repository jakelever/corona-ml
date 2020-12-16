
import argparse


def format_time(elapsed):
	'''
	Takes a time in seconds and returns a string hh:mm:ss
	'''
	# Round to the nearest second.
	elapsed_rounded = int(round((elapsed)))

	# Format as hh:mm:ss
	return str(datetime.timedelta(seconds=elapsed_rounded))

# Function to calculate the accuracy of our predictions vs labels
def flat_accuracy(preds, labels):
	pred_flat = np.argmax(preds, axis=1).flatten()
	labels_flat = labels.flatten()
	return np.sum(pred_flat == labels_flat) / len(labels_flat)

# Function to calculate the accuracy of our predictions vs labels
def all_measures(preds, labels):
	pred_flat = np.argmax(preds, axis=1).flatten()
	labels_flat = labels.flatten()

	TP = ((pred_flat==labels_flat) & labels_flat).sum()
	TN = ((pred_flat==labels_flat) & (1-labels_flat)).sum()
	FN = ((pred_flat!=labels_flat) & labels_flat).sum()
	FP = ((pred_flat!=labels_flat) & (1-labels_flat)).sum()
	precision = TP / (TP+FP) if (TP+FP) != 0 else 0
	recall = TP / (TP+FN) if (TP+FN) != 0 else 0
	accuracy = (TP+TN) / (TP+TN+FN+FP)
	f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) != 0 else 0

	class_balance = pred_flat.sum() / len(pred_flat)

	return precision, recall, accuracy, f1, class_balance

def loadData(filename):
	labels, docs = [],[]
	with open(filename) as f:
		data = json.load(f)
		for doc in data:
			pmid = doc['pmid']
			label_bool = doc['isDrugRepurposing']
			title_texts = doc['titleText']
			abstract_texts = doc['abstractText']
			label = 1 if label_bool else 0
			doc = "\n".join(title_texts + abstract_texts)
			labels.append(label)
			docs.append(doc)
	return labels, docs

def getDevice():
	# If there's a GPU available...
	if torch.cuda.is_available():    
		# Tell PyTorch to use the GPU.    
		device = torch.device("cuda")

		print('There are %d GPU(s) available.' % torch.cuda.device_count())

		print('We will use the GPU:', torch.cuda.get_device_name(0))

		# If not...
	else:
		print('No GPU available, using the CPU instead.')
		device = torch.device("cpu")
	return device

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Apply a document classifier')
	parser.add_argument('--model',required=True,type=str,help='Directory with document classifier model')
	parser.add_argument('--kaggleMetadataFile',required=True,type=str,help='KAGGLE metadata file')
	#parser.add_argument('--wordlist',required=True,type=str,help='Wordlist with chemical terms')
	parser.add_argument('--outFile',required=True,type=str,help='Output file')
	args = parser.parse_args()

	import json
	import torch
	import tensorflow as tf
	from transformers import BertTokenizer
	from keras.preprocessing.sequence import pad_sequences
	from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
	from transformers import BertForSequenceClassification, AdamW, BertConfig
	from transformers import get_linear_schedule_with_warmup
	import numpy as np
	import time
	import datetime
	import random
	import os
	import shutil
	from scipy.special import softmax
	import kindred
	import csv
	from collections import Counter

	#HUGGING_FACE_MODEL = 'bert-base-uncased'
	HUGGING_FACE_MODEL = 'monologg/biobert_v1.1_pubmed'
	MAX_LEN = 256
	batch_size = 32
	epochs = 4

	device = getDevice()

	# Load the BERT tokenizer.
	print('Loading BERT tokenizer...')
	tokenizer = BertTokenizer.from_pretrained(HUGGING_FACE_MODEL, do_lower_case=True)

	kaggle_docs = []
	kaggle_metadata = []
	virus_keywords = {}
	virus_keywords['SARS-CoV-2'] = ['covid-19','covid 19','sars-cov-2','sars cov 2','sars-cov 2','sars cov-2','sars-cov2','sars cov2','sarscov2',]
	virus_keywords['SARS-CoV'] = ['sars-cov','sars cov','severe acute respiratory syndrome']
	virus_keywords['MERS-CoV'] = ['mers-cov-2','mers cov 2','mers-cov 2','mers cov-2','mers cov2','mers-cov2','merscov2',]

	virus_doc_counts = Counter()

	with open(args.kaggleMetadataFile, newline='') as csvfile:
		csvreader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
		for i,row in enumerate(csvreader):

			combined_text = "%s\n%s" % (row['title'],row['abstract'])
			combined_text_lower = combined_text.lower()
			#print(combined_text)
			#assert False

			found_viruses = set()
			for virus in ['SARS-CoV-2','SARS-CoV','MERS-CoV']:
				for keyword in virus_keywords[virus]:
					if keyword in combined_text_lower:
						found_viruses.add(virus)
						combined_text_lower = combined_text_lower.replace(keyword,'#'*10)

			if len(found_viruses) == 0:
				continue

			#if len(kaggle_docs) > 1000:
			#	break

			row['viruses'] = sorted(found_viruses)
			for virus in row['viruses']:
				virus_doc_counts[virus] += 1

			kaggle_docs.append(combined_text)
			kaggle_metadata.append(row)

	print("Loaded %d total documents with keywords" % len(kaggle_docs))
	for virus in sorted(virus_doc_counts.keys()):
		print("Found %d documents with keywords for %s" % (virus_doc_counts[virus],virus))

	kaggle_encoded = [ tokenizer.encode(doc,add_special_tokens = True) for doc in kaggle_docs ]

	kaggle_padded = pad_sequences(kaggle_encoded, maxlen=MAX_LEN, dtype="long", 
				    value=0, truncating="post", padding="post")
	kaggle_padded = torch.tensor(kaggle_padded)

	kaggle_masks = [ [int(token_id > 0) for token_id in doc] for doc in kaggle_padded ]
	kaggle_masks = torch.tensor(kaggle_masks)

	model = BertForSequenceClassification.from_pretrained(args.model)

	model.eval()
	model.cuda()

	kaggle_indices = torch.tensor(list(range(kaggle_padded.shape[0])))
	kaggle_data = TensorDataset(kaggle_padded, kaggle_masks, kaggle_indices)
	kaggle_sampler = SequentialSampler(kaggle_data)
	kaggle_dataloader = DataLoader(kaggle_data, sampler=kaggle_sampler, batch_size=batch_size)

	kaggle_predictions = {}

	# Evaluate data for one epoch
	for batch in kaggle_dataloader:

		input_ids, input_mask, input_indices = batch

		b_input_ids = input_ids.to(device)
		b_input_mask = input_mask.to(device)

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
			kaggle_predictions[input_index.int()] = prediction


	with open(args.outFile,'w') as outF:
		for index,kaggle_prediction in kaggle_predictions.items():
			kaggle_doc = kaggle_docs[index]
			metadata = kaggle_metadata[index]
			if kaggle_prediction > 0.7:
				outData = [kaggle_prediction,metadata['source_x'],metadata['cord_uid'],metadata['title'],"|".join(metadata['viruses'])]
				outF.write("\t".join(map(str,outData)) + "\n")

if False:
	kaggle_corpus = kindred.Corpus()
	for index,kaggle_prediction in kaggle_predictions.items():
		kaggle_doc = kaggle_docs[index]
		kaggle_title = kaggle_titles[index]
		if kaggle_prediction > 0.7:
			kaggle_corpus.addDocument(kindred.Document(kaggle_doc,metadata={'score':kaggle_prediction,'title':kaggle_title}))

	parser = kindred.Parser(model='en_core_sci_sm')
	parser.parse(kaggle_corpus)

	termLookup = kindred.EntityRecognizer.loadWordlists({'chemical':args.wordlist}, idColumn=0, termsColumn=2)
	ner = kindred.EntityRecognizer(termLookup)
	ner.annotate(kaggle_corpus)

	for doc in kaggle_corpus.documents:
		entities = sorted(set([ e.text.lower() for e in doc.entities ]))

		outData = [ doc.metadata['score'], doc.metadata['title'], "|".join(entities) ]
		#print(outData)
		print("\t".join(map(str,outData)))

