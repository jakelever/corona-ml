
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
	parser = argparse.ArgumentParser(description='Train a document classifier')
	parser.add_argument('--documents',required=True,type=str,help='JSON file with documents')
	parser.add_argument('--outDir',required=True,type=str,help='Output directory to store model')
	args = parser.parse_args()

	import json
	import torch
	import tensorflow as tf
	from transformers import BertTokenizer
	from keras.preprocessing.sequence import pad_sequences
	from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
	from transformers import BertForSequenceClassification, AdamW, BertConfig
	from transformers import get_linear_schedule_with_warmup
	from sklearn.model_selection import train_test_split
	import numpy as np
	import time
	import datetime
	import random
	import os
	import shutil

	#HUGGING_FACE_MODEL = 'bert-base-uncased'
	HUGGING_FACE_MODEL = 'monologg/biobert_v1.1_pubmed'
	MAX_LEN = 256
	batch_size = 32
	epochs = 4

	#train_labels, train_docs = loadData(args.train)
	#dev_labels, dev_docs = loadData(args.dev)
	
	doc_texts, labels = [], []
	with open(args.documents) as f:
		documents = json.load(f)
		annotated = [ d for d in documents if d['annotations'] ]
		for d in annotated:
			#doc_text = d['title'] + '\n' + d['abstract']
			doc_text = d['title']
			doc_texts.append(doc_text)
			
			#target = 'Viral Biology' in d['annotations'] or 'Host Biology' in d['annotations']
			#target = 'Novel Therapeutics' in d['annotations'] or 'Drug Repurposing' in d['annotations']
			target = 'Transmission' in d['annotations']
			label = 1 if target else 0
			labels.append(label)
			
	assert sum(labels) > 0 and sum(labels) < len(labels), "Got %d positive labels of %d" % (sum(labels),len(labels))
			
	train_docs, dev_docs, train_labels, dev_labels = train_test_split(doc_texts, labels, test_size=0.33, random_state=42)

	print("Train size: %d" % len(train_labels))
	print("Train class balance: %.1f%%" % (100*sum(train_labels)/len(train_labels)))
	print("Dev size: %d" % len(dev_labels))
	print("Dev class balance: %.1f%%" % (100*sum(dev_labels)/len(dev_labels)))
	#assert False

	train_labels = torch.tensor(train_labels)
	dev_labels = torch.tensor(dev_labels)

	device = getDevice()

	# Load the BERT tokenizer.
	print('Loading BERT tokenizer...')
	tokenizer = BertTokenizer.from_pretrained(HUGGING_FACE_MODEL, do_lower_case=True)

	train_encoded = [ tokenizer.encode(doc,add_special_tokens = True,max_length=MAX_LEN,truncation=True) for doc in train_docs ]
	dev_encoded = [ tokenizer.encode(doc,add_special_tokens = True,max_length=MAX_LEN,truncation=True) for doc in dev_docs ]
	print("Max train length = %d" % (max( len(e) for e in train_encoded )))
	print("Max dev length = %d" % (max( len(e) for e in dev_encoded )))




	train_padded = pad_sequences(train_encoded, maxlen=MAX_LEN, dtype="long", 
				    value=0, truncating="post", padding="post")
	dev_padded = pad_sequences(dev_encoded, maxlen=MAX_LEN, dtype="long", 
				    value=0, truncating="post", padding="post")

	train_padded = torch.tensor(train_padded)
	dev_padded = torch.tensor(dev_padded)

	train_masks = [ [int(token_id > 0) for token_id in doc] for doc in train_padded ]
	dev_masks = [ [int(token_id > 0) for token_id in doc] for doc in dev_padded ]

	train_masks = torch.tensor(train_masks)
	dev_masks = torch.tensor(dev_masks)


	# Create the DataLoader for our training set.
	train_data = TensorDataset(train_padded, train_masks, train_labels)
	train_sampler = RandomSampler(train_data)
	train_dataloader = DataLoader(train_data, sampler=train_sampler, batch_size=batch_size)

	# Create the DataLoader for our validation set.
	dev_data = TensorDataset(dev_padded, dev_masks, dev_labels)
	dev_sampler = SequentialSampler(dev_data)
	dev_dataloader = DataLoader(dev_data, sampler=dev_sampler, batch_size=batch_size)



	# Load BertForSequenceClassification, the pretrained BERT model with a single 
	# linear classification layer on top. 
	model = BertForSequenceClassification.from_pretrained(
	    HUGGING_FACE_MODEL, # Use the 12-layer BERT model, with an uncased vocab.
	    num_labels = 2, # The number of output labels--2 for binary classification.
			    # You can increase this for multi-class tasks.   
	    output_attentions = False, # Whether the model returns attentions weights.
	    output_hidden_states = False, # Whether the model returns all hidden-states.
	)

	# Tell pytorch to run this model on the GPU.
	model.cuda()

	# Note: AdamW is a class from the huggingface library (as opposed to pytorch) 
	# I believe the 'W' stands for 'Weight Decay fix"
	optimizer = AdamW(model.parameters(),
			  lr = 2e-5, # args.learning_rate - default is 5e-5, our notebook had 2e-5
			  eps = 1e-8 # args.adam_epsilon  - default is 1e-8.
			)



	# Total number of training steps is number of batches * number of epochs.
	total_steps = len(train_dataloader) * epochs

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
	for epoch_i in range(0, epochs):
    
		# ========================================
		#               Training
		# ========================================

		# Perform one full pass over the training set.

		print("")
		print('======== Epoch {:} / {:} ========'.format(epoch_i + 1, epochs))
		print('Training...')

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
			if step % 40 == 0 and not step == 0:
				# Calculate elapsed time in minutes.
				elapsed = format_time(time.time() - t0)
	
				# Report progress.
				print('  Batch {:>5,}  of  {:>5,}.    Elapsed: {:}.'.format(step, len(train_dataloader), elapsed))

			# Unpack this training batch from our dataloader. 
			#
			# As we unpack the batch, we'll also copy each tensor to the GPU using the 
			# `to` method.
			#
			# `batch` contains three pytorch tensors:
			#   [0]: input ids 
			#   [1]: attention masks
			#   [2]: labels 
			b_input_ids = batch[0].to(device)
			b_input_mask = batch[1].to(device)
			b_labels = batch[2].to(device)

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

		print("")
		print("  Average training loss: {0:.2f}".format(avg_train_loss))
		print("  Training epoch took: {:}".format(format_time(time.time() - t0)))

		# ========================================
		#               Validation
		# ========================================
		# After the completion of each training epoch, measure our performance on
		# our validation set.

		print("")
		print("Running Validation...")

		t0 = time.time()

		# Put the model in evaluation mode--the dropout layers behave differently
		# during evaluation.
		model.eval()

		# Tracking variables 
		eval_loss = 0
		eval_precision = 0
		eval_recall = 0
		eval_accuracy = 0
		eval_f1 = 0
		eval_class_balance = 0
		nb_eval_steps, nb_eval_examples = 0, 0

		# Evaluate data for one epoch
		for batch in dev_dataloader:
        
			# Add batch to GPU
			batch = tuple(t.to(device) for t in batch)

			# Unpack the inputs from our dataloader
			b_input_ids, b_input_mask, b_labels = batch

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
			label_ids = b_labels.to('cpu').numpy()

			# Calculate the accuracy for this batch of test sentences.
			#tmp_eval_accuracy = flat_accuracy(logits, label_ids)
			tmp_precision, tmp_recall, tmp_accuracy, tmp_f1, tmp_class_balance = all_measures(logits, label_ids)

			# Accumulate the total accuracy.
			eval_precision += tmp_precision
			eval_recall += tmp_recall
			eval_accuracy += tmp_accuracy
			eval_f1 += tmp_f1
			eval_class_balance += tmp_class_balance

			# Track the number of batches
			nb_eval_steps += 1

		# Report the final accuracy for this validation run.
		print("  Precision: {0:.2f}".format(eval_precision/nb_eval_steps))
		print("  Recall: {0:.2f}".format(eval_recall/nb_eval_steps))
		print("  Accuracy: {0:.2f}".format(eval_accuracy/nb_eval_steps))
		print("  F1: {0:.2f}".format(eval_f1/nb_eval_steps))
		print("  Class balance: {0:.2f}".format(eval_class_balance/nb_eval_steps))
		print("  Validation took: {:}".format(format_time(time.time() - t0)))


	print()
	print("#"*30)
	print("Saving model to %s" % args.outDir)
	if os.path.isdir(args.outDir):
		shutil.rmtree(args.outDir)
	os.mkdir(args.outDir)
	model.save_pretrained(args.outDir)

