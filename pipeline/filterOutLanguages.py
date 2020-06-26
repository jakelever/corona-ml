from collections import Counter
from utils import load_documents,detect_language

documents = load_documents('alldocuments.json')

languageCounter = Counter()
filteredCount = 0
with open('languageFiltered.tsv','w') as outF:
	for doc in documents:
		combined_text = doc['title'] + '\n' + doc['abstract']
		
		languages = detect_language(combined_text)
		languageCounter += Counter(languages)
		
		if len(languages) > 0:
			filteredCount += 1
			outData = [doc['cord_uid'],doc['pubmed_id'],",".join(languages),doc['url']]
			outF.write("\t".join(outData) + "\n")
		
print(languageCounter)
print("Filtered %d documents with non-english language" % filteredCount)
