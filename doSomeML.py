
from utils import dbconnect,load_documents_with_annotations

mydb = dbconnect()

documents = load_documents_with_annotations('alldocuments.json',mydb)
	
Xtext = []
y = []
	
for doc in documents:	
	if len(doc['annotations']) == 0:
		continue
		
	if 'RemoveFromCorpus?' in doc['annotations']:
		continue
	if 'NotAllEnglish' in doc['annotations']:
		continue
	
	combined_text = doc['title'] + '\n' + doc['abstract']
	Xtext.append(combined_text)
	
	if 'pub_type' in doc:
		inPubtype = any('clinical trial' in pt.lower() for pt in doc['pub_type'])
		inAnnotations = 'Clinical trial' in doc['annotations']
		if inPubtype and not inAnnotations:
			print(doc['title'])
	
	if 'Review' in doc['annotations']:
	#if 'Novel Therapeutics' in doc['annotations'] or 'Drug Repurposing' in doc['annotations']:
		y.append(1)
	else:
		y.append(0)
		
print("Number of docs = ", len(Xtext))
print("Class balance = ", sum(y) / len(y))

from sklearn.model_selection import train_test_split
Xtext_train, Xtext_test, y_train, y_test = train_test_split(Xtext, y, test_size=0.33, random_state=42)
#import random
#indices = list(range(len(y)))
#random.shuffle(indices)
#train_indices = indices[:round(len(indices)*0.66)]
#test_indices = indices[round(len(indices)*0.66):]

#Xtext_train = [ Xtext[i] for i in train_indices ]
#Xtext_test = [ Xtext[i] for i in test_indices ]
#y_train = [ y[i] for i in train_indices ]
#y_test = [ y[i] for i in test_indices ]

from sklearn.feature_extraction.text import CountVectorizer
count_vect = CountVectorizer()
X_train = count_vect.fit_transform(Xtext_train)
X_test = count_vect.transform(Xtext_test)

from sklearn.feature_extraction.text import TfidfTransformer
#tf_transformer = TfidfTransformer()
#X_train = count_vect.fit_transform(Xtext_train)
#X_test = count_vect.transform(Xtext_test)

#from sklearn.naive_bayes import MultinomialNB
#clf = MultinomialNB()

#from sklearn.linear_model import LogisticRegression
#clf = LogisticRegression(random_state=0)

from sklearn.svm import LinearSVC
clf = LinearSVC(random_state=0, tol=1e-5)

clf.fit(X_train,y_train)

predicted = clf.predict(X_test)

import sklearn.metrics

f1_score = sklearn.metrics.f1_score(y_test,predicted)
precision_score = sklearn.metrics.precision_score(y_test,predicted)
recall_score = sklearn.metrics.recall_score(y_test,predicted)

print("f1_score", f1_score)
print("precision_score", precision_score)
print("recall_score", recall_score)
