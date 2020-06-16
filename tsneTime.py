from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation
from sklearn.manifold import TSNE
from collections import Counter
from utils import dbconnect,load_documents_with_annotations,cleanup_documents
import random

random.seed(42)

mydb = dbconnect()

documents = load_documents_with_annotations('alldocuments.json',mydb,task_ids=[2])
cleanup_documents(documents)
	
filters = {'RemoveFromCorpus?','NotAllEnglish'}
filters.update({'Updates','Comment','News','Meta-analysis','Guidelines'})

#documents = [ d for d in documents if len(d['annotations']) > 0 ]
documents = [ d for d in documents if not any (f in d['annotations'] for f in filters) ]


#documents = [ d for d in documents if len(d['annotations']) > 0 or random.random() > 0.9 ]


allText = [ d['title'] + '\n' + d['abstract'] for d in documents ]


n_features = 1000
n_components = 20

n_features = 10000
n_components = 100

option = 2
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
	
tsne = TSNE(n_components=2)
tsned = tsne.fit_transform(topiced)

print("tsned.shape",tsned.shape)

assert tsned.shape == (len(documents),2)

with open('tsne.tsv','w',encoding='utf-8') as outF:
	for i,doc in enumerate(documents):
		title = doc['title']
		journal = doc['journal']
		publish_year = doc['publish_year']
		url = doc['url']
		annotations = "|".join(doc['annotations'])
		embedded = tsned[i,:].tolist()
		
		outData = [i, title, journal, publish_year, url,annotations] + embedded
		outLine = "\t".join(map(str,outData))
		assert len(outLine.split('\t')) == len(outData)
		outF.write(outLine + "\n")
		