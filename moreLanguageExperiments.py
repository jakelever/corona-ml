from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation
from collections import Counter
from utils import load_documents,cleanup_documents
import numpy as np
import random
import nltk
from nltk.corpus import stopwords
import re

# https://stackoverflow.com/questions/30069846/how-to-find-out-chinese-or-japanese-character-in-a-string-in-python
def is_cjk(character):
    """"
    Checks whether character is CJK.

        >>> is_cjk(u'\u33fe')
        True
        >>> is_cjk(u'\uFE5F')
        False

    :param character: The character that needs to be checked.
    :type character: char
    :return: bool
    """
    return any([start <= ord(character) <= end for start, end in 
                [(4352, 4607), (11904, 42191), (43072, 43135), (44032, 55215), 
                 (63744, 64255), (65072, 65103), (65381, 65500), 
                 (131072, 196607)]
                ])

documents = load_documents('alldocuments.json')
cleanup_documents(documents)

#documents = documents[:10000]
#print(sorted(stopwords.words('french')))

#print(help(stopwords.words))

english = set(stopwords.words('english') + ['se','sera','et'])

filterWords = {}
filterWords['french'] = [ word for word in set(stopwords.words('french')) if not word in english and len(word) >= 2 ]
filterWords['german'] = [ word for word in set(stopwords.words('german')) if not word in english and len(word) >= 2 ]
filterWords['spanish'] = [ word for word in set(stopwords.words('spanish')) if not word in english and len(word) >= 2 ]

filterREs = {}
for language,words in filterWords.items():
	filterREs[language] = [ re.compile(r'\s%s\s' % re.escape(word)) for word in words ]
	print(language, words)
	

found = Counter()
for doc in documents:
	combined_text_lower = (doc['title'] + '\n' + doc['abstract']).lower()
	for language,regexes in filterREs.items():
		matching = [ 1 for regex in regexes if regex.search(combined_text_lower) ]
		if len(matching) >= 5:
			#print(language,doc['url'],doc['title'],matching)
			found[language] += 1
			
	if any(is_cjk(c) for c in combined_text_lower):
		#print('CJK',doc['url'],doc['title'])
		found['cjk'] += 1
		
print(found)