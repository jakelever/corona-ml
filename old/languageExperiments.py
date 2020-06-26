from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation
from collections import Counter
from utils import load_documents,cleanup_documents
import numpy as np
import random

documents = load_documents('alldocuments.json')
cleanup_documents(documents)

#documents = documents[:10000]

allText = [ d['title'] + '\n' + d['abstract'] for d in documents ]

vectorizer = CountVectorizer(stop_words='english')
vectorized = vectorizer.fit_transform(allText)
#print(vectorized.shape)

vectorized = (vectorized > 0.5).astype(np.int_)

words = vectorizer.get_feature_names()
#print(random.sample(words,10))
word_index = words.index('la')
word_vector = vectorized[:,word_index]

#print(vectorized.shape)
#print(word_vector.shape)

cooccurs = vectorized.T.dot(word_vector).todense()
#print(type(cooccurs), cooccurs.shape)
#word_vector = 
#get_feature_names()

#print(cooccurs.sum())
ind = cooccurs.argsort()
#print(ind.shape)
#print(ind[:-10,0])

with_words = [ (score[0],word) for score,word in zip(cooccurs.tolist(),words) ]
with_words = sorted(with_words,reverse=True)

for count,word in with_words[:20]:
	print("%d\t%s" % (count,word))
#print(with_words[-10:])
