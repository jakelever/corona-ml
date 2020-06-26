from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation
from sklearn.manifold import TSNE
from collections import Counter
from utils import dbconnect,load_documents_with_annotations,cleanup_documents,filter_languages
import random
import json

random.seed(42)

mydb = dbconnect()

documents = load_documents_with_annotations('alldocuments.json',mydb,task_ids=[2])
cleanup_documents(documents)
	
filters = {'RemoveFromCorpus?','NotAllEnglish'}
documents = [ d for d in documents if not any (f in d['annotations'] for f in filters) ]
documents = filter_languages(documents)

#documents = [ d for d in documents if len(d['annotations']) > 0 ]
#documents = [ d for d in documents if len(d['annotations']) > 0 or random.random() > 0.9 ]

print(len(documents))

allText = [ d['title'] + '\n' + d['abstract'] for d in documents ]

n_features = 1000
n_components = 20

#n_features = 10000
#n_components = 100

option = 1
if option == 1:
	vectorizer = TfidfVectorizer(max_df=0.95, min_df=2,
									   max_features=n_features,
									   stop_words='english')
									   
	model = NMF(n_components=n_components, random_state=1,
			  alpha=.1, l1_ratio=.5)
elif option == 2:	  
	vectorizer = CountVectorizer(max_df=0.95, min_df=2,
									max_features=n_features,
									stop_words='english')
									
	model = LatentDirichletAllocation(n_components=n_components, max_iter=5,
									learning_method='online',
									learning_offset=50.,
									random_state=0)
		  
print("len(documents)",len(documents))

vectorized = vectorizer.fit_transform(allText)
print("vectorized.shape",vectorized.shape)
topiced = model.fit_transform(vectorized)
print("topiced.shape",topiced.shape)
	
for i,doc in enumerate(documents):
	doc['embedding'] = topiced[i,:].tolist()
	
with open('embeddings.json','w',encoding='utf-8') as f:
	json.dump(documents,f)

#documents = [ d for d in documents if len(d['annotations']) > 0 ]
#documents = [ d for d in documents if not 'Review' in d['annotations'] ]

