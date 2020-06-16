from utils import dbconnect,load_documents_with_annotations,detect_language

mydb = dbconnect()

documents = load_documents_with_annotations('alldocuments.json',mydb)

documents = [ doc for doc in documents if len(doc['annotations']) > 0 ]

for doc in documents:
	combined_text = doc['title'] + '\n' + doc['abstract']
	
	languages = detect_language(combined_text)
	
	isAnnotatedNonEnglish = 'NotAllEnglish' in doc['annotations']
	
	match = None
	if isAnnotatedNonEnglish and len(languages) > 0:
		match = 'TP'
	elif isAnnotatedNonEnglish and len(languages) == 0:
		match = 'FN'
	elif not isAnnotatedNonEnglish and len(languages) > 0:
		match = 'FP'
	
	if match:
		print("\t".join([match,",".join(languages),doc['title'],doc['url']]))
	