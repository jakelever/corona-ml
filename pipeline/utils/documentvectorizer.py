from sklearn.preprocessing import OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from scipy.sparse import hstack

class DocumentVectorizer():
	def __init__(self,features=None):
		self.fitted = False
		if features:
			self.features = features
		else:
			self.features = ['journal','titleabstract']
						
	def set_params(self,features=None):
		if features:
			self.features = features
		else:
			self.features = ['journal','titleabstract']
	
	def fit_transform(self,docs,*args):
		assert self.fitted == False
		self.fitted = True
		
		self.title_vectorizer = TfidfVectorizer(stop_words='english',ngram_range=(1,2))
		self.abstract_vectorizer = TfidfVectorizer(stop_words='english',ngram_range=(1,2))
		self.titleabstract_vectorizer = TfidfVectorizer(stop_words='english',ngram_range=(1,2))
		self.journal_vectorizer = OneHotEncoder(handle_unknown='ignore')
		
		X = []
		if 'title' in self.features:
			X.append(self.title_vectorizer.fit_transform( [ d['title'] for d in docs ] ))
		if 'abstract' in self.features:
			X.append(self.abstract_vectorizer.fit_transform( [ d['abstract'] for d in docs ] ))
		if 'titleabstract' in self.features:
			X.append(self.titleabstract_vectorizer.fit_transform( [ d['title'] + "\n" + d['abstract'] for d in docs ] ))
		if 'journal' in self.features:
			X.append(self.journal_vectorizer.fit_transform( [ [d['journal']] for d in docs ] ))
			
		X = hstack(X)
		X = X.tocsr()
		
		return X
	
	def transform(self,docs,*args):
		assert self.fitted == True
		
		X = []
		if 'title' in self.features:
			X.append(self.title_vectorizer.transform( [ d['title'] for d in docs ] ))
		if 'abstract' in self.features:
			X.append(self.abstract_vectorizer.transform( [ d['abstract'] for d in docs ] ))
		if 'titleabstract' in self.features:
			X.append(self.titleabstract_vectorizer.transform( [ d['title'] + "\n" + d['abstract'] for d in docs ] ))
		if 'journal' in self.features:
			X.append(self.journal_vectorizer.transform( [ [d['journal']] for d in docs ] ))
		
		X = hstack(X)
		X = X.tocsr()
		
		return X
