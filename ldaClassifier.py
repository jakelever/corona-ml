from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation
from collections import Counter
from utils import dbconnect,load_documents_with_annotations

mydb = dbconnect()

documents = load_documents_with_annotations('alldocuments.json',mydb)
	
Xtext = []
y = []

allText = []
	
for doc in documents:
		
	if 'RemoveFromCorpus?' in doc['annotations']:
		continue
	if 'NotAllEnglish' in doc['annotations']:
		#print('NotAllEnglish', doc['title'])
		continue
		
	combined_text = doc['title'] + '\n' + doc['abstract']
	
	#if re.search(r'\bdes\b',combined_text, re.IGNORECASE):
	#	print("HUH?", doc['title'])
		
	allText.append(combined_text)
		
	if len(doc['annotations']) == 0:
		continue
	
	Xtext.append(combined_text)
	
	if 'pub_type' in doc:
		inPubtype = any('clinical trial' in pt.lower() for pt in doc['pub_type'])
		inAnnotations = 'Clinical trial' in doc['annotations']
		#if inPubtype and not inAnnotations:
		#	print(doc['title'])
	
	if any(label in doc['annotations'] for label in ['Drug repurposing','Novel therapeutics']):
	#if 'Novel Therapeutics' in doc['annotations'] or 'Drug Repurposing' in doc['annotations']:
		y.append(1)
	else:
		y.append(0)
	
print("Number of docs = ", len(Xtext))
print("Number positive = ", sum(y))
print("Class balance = ", sum(y) / len(y))

from sklearn.model_selection import train_test_split
Xtext_train, Xtext_test, y_train, y_test = train_test_split(Xtext, y, test_size=0.33, random_state=42)

n_features = 1000
n_components = 20

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
		  
vectorized = vectorizer.fit_transform(allText)
model.fit(vectorized)
		  
vectorized_train = vectorizer.transform(Xtext_train)
topic_weights = model.transform(vectorized_train)

print(len(Xtext_train))
print(topic_weights.shape)

posTopics = Counter()
negTopics = Counter()

for i in range(len(Xtext_train)):
	topTopic = topic_weights[i,:].argmax()	
	if y_train[i]:
		posTopics[topTopic] += 1
		titleIsh = Xtext_train[i][:100].replace('\n',' ')
		#print("%d\t%s" % (topTopic,titleIsh))
	else:
		negTopics[topTopic] += 1
		
feature_names = vectorizer.get_feature_names()
n_top_words = 10
for topic_idx, topic in enumerate(model.components_):
	message = "%d\t%d\t" % (posTopics[topic_idx],negTopics[topic_idx])
	message += "Topic #%d: " % topic_idx
	message += " ".join([feature_names[i]
					 for i in topic.argsort()[:-n_top_words - 1:-1]])
	print(message)
print()
