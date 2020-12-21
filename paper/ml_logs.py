#!/usr/bin/env python

import os
import json
import pandas as pd

dir_name = 'ml_logs'
log_files = [ os.path.join(dir_name,f) for f in os.listdir(dir_name) if f.endswith('txt' )]
print(len(log_files))

log_data = []
for log_file in log_files:
  with open(log_file) as f:
    curly_lines = [ line for line in f if line.startswith('{') ]
    assert len(curly_lines) == 1
    json_data = json.loads(curly_lines[0])
    log_data.append(json_data)

print(len(log_data))

ml_data = []
for l in log_data:
  epochs, learning_rate = None,None
  
  is_bert = l['params']['clf'] == 'BERT'
  if is_bert:
    model = l['params']['clf_model']
    epochs = l['params']['clf_epochs']
    learning_rate = l['params']['clf_learning_rate']
    #if epochs < 16 or learning_rate > 4e-5:
    #  continue
  else:
    model = l['params']['clf']
    #epochs = l['params']['clf_epochs']
    #learning_rate = l['params']['clf_learning_rate']
    
  if model == '/home/groups/rbaltman/jlever/bluebert/base_uncased_pubmedANDmimicIII/':
    model = 'bluebert/base_uncased'
    
  model = model.replace('microsoft/BiomedNLP-PubMedBERT-base-uncased-','microsoft/PubMedBERT-')
  
  macro_f1 = l['results']['MACRO']['f1_score']
  ml_data.append([is_bert,model,epochs,learning_rate,macro_f1])

ml_df = pd.DataFrame(ml_data,columns=['is_bert','model','epochs','learning_rate','macro_f1'])
