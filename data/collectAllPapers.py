import argparse
import os
import csv
import json
import xml.etree.cElementTree as etree
import html
import re
import calendar
import unicodedata
from datetime import date,datetime
import string
import calendar
import sys
import gzip

pubTypeSkips = {"Research Support, N.I.H., Intramural","Research Support, Non-U.S. Gov't","Research Support, U.S. Gov't, P.H.S.","Research Support, N.I.H., Extramural","Research Support, U.S. Gov't, Non-P.H.S.","English Abstract"}

# Remove empty brackets (that could happen if the contents have been removed already
# e.g. for citation ( [3] [4] ) -> ( ) -> nothing
def removeBracketsWithoutWords(text):
	fixed = re.sub(r'\([\W\s]*\)', ' ', text)
	fixed = re.sub(r'\[[\W\s]*\]', ' ', fixed)
	fixed = re.sub(r'\{[\W\s]*\}', ' ', fixed)
	return fixed

# Some older articles have titles like "[A study of ...]."
# This removes the brackets while retaining the full stop
def removeWeirdBracketsFromOldTitles(titleText):
	titleText = titleText.strip()
	if titleText[0] == '[' and titleText[-2:] == '].':
		titleText = titleText[1:-2] + '.'
	return titleText

def cleanupText(text):
	# Remove some "control-like" characters (left/right separator)
	text = text.replace(u'\u2028',' ').replace(u'\u2029',' ')
	text = "".join(ch for ch in text if unicodedata.category(ch)[0]!="C")
	text = "".join(ch if unicodedata.category(ch)[0]!="Z" else " " for ch in text)

	# Remove repeated commands and commas next to periods
	text = re.sub(',(\s*,)*',',',text)
	text = re.sub('(,\s*)*\.','.',text)
	return text.strip()

# XML elements to ignore the contents of
ignoreList = ['table', 'table-wrap', 'xref', 'disp-formula', 'inline-formula', 'ref-list', 'bio', 'ack', 'graphic', 'media', 'tex-math', 'mml:math', 'object-id', 'ext-link']

# XML elements to separate text between
separationList = ['title', 'p', 'sec', 'break', 'def-item', 'list-item', 'caption']
def extractTextFromElem(elem):
	# Extract any raw text directly in XML element or just after
	head = ""
	if elem.text:
		head = elem.text
	tail = ""
	if elem.tail:
		tail = elem.tail
	
	# Then get the text from all child XML nodes recursively
	childText = []
	for child in elem:
		childText = childText + extractTextFromElem(child)
		
	# Check if the tag should be ignore (so don't use main contents)
	if elem.tag in ignoreList:
		return [tail.strip()]
	# Add a zero delimiter if it should be separated
	elif elem.tag in separationList:
		return [0] + [head] + childText + [tail]
	# Or just use the whole text
	else:
		return [head] + childText + [tail]
	

# Merge a list of extracted text blocks and deal with the zero delimiter
def extractTextFromElemList_merge(list):
	textList = []
	current = ""
	# Basically merge a list of text, except separate into a new list
	# whenever a zero appears
	for t in list:
		if t == 0: # Zero delimiter so split
			if len(current) > 0:
				textList.append(current)
				current = ""
		else: # Just keep adding
			current = current + " " + t
			current = current.strip()
	if len(current) > 0:
		textList.append(current)
	return textList
	
# Main function that extracts text from XML element or list of XML elements
def extractTextFromElemList(elemList):
	textList = []
	# Extracts text and adds delimiters (so text is accidentally merged later)
	if isinstance(elemList, list):
		for e in elemList:
			textList = textList + extractTextFromElem(e) + [0]
	else:
		textList = extractTextFromElem(elemList) + [0]

	# Merge text blocks with awareness of zero delimiters
	mergedList = extractTextFromElemList_merge(textList)
	
	# Remove any newlines (as they can be trusted to be syntactically important)
	mergedList = [ text.replace('\n', ' ') for text in mergedList ]

	# Remove no-break spaces
	mergedList = [ cleanupText(text) for text in mergedList ]
	
	return mergedList

def getJournalDateForMedlineFile(elem,pmid):
	yearRegex = re.compile(r'(18|19|20)\d\d')

	monthMapping = {}
	for i,m in enumerate(calendar.month_name):
		monthMapping[m] = i
	for i,m in enumerate(calendar.month_abbr):
		monthMapping[m] = i

	# Try to extract the publication date
	pubDateField = elem.find('./MedlineCitation/Article/Journal/JournalIssue/PubDate')
	medlineDateField = elem.find('./MedlineCitation/Article/Journal/JournalIssue/PubDate/MedlineDate')

	assert not pubDateField is None, "Couldn't find PubDate field for PMID=%s" % pmid

	medlineDateField = pubDateField.find('./MedlineDate')
	pubDateField_Year = pubDateField.find('./Year')
	pubDateField_Month = pubDateField.find('./Month')
	pubDateField_Day = pubDateField.find('./Day')

	pubYear,pubMonth,pubDay = None,None,None
	if not medlineDateField is None:
		regexSearch = re.search(yearRegex,medlineDateField.text)
		if regexSearch:
			pubYear = regexSearch.group()
		monthSearch = [ c for c in (list(calendar.month_name) + list(calendar.month_abbr)) if c != '' and c in medlineDateField.text ]
		if len(monthSearch) > 0:
			pubMonth = monthSearch[0]
	else:
		if not pubDateField_Year is None:
			pubYear = pubDateField_Year.text
		if not pubDateField_Month is None:
			pubMonth = pubDateField_Month.text
		if not pubDateField_Day is None:
			pubDay = pubDateField_Day.text

	if not pubYear is None:
		pubYear = int(pubYear)
		if not (pubYear > 1700 and pubYear < 2100):
			pubYear = None

	if not pubMonth is None:
		if pubMonth in monthMapping:
			pubMonth = monthMapping[pubMonth]
		pubMonth = int(pubMonth)
	if not pubDay is None:
		pubDay = int(pubDay)

	return pubYear,pubMonth,pubDay

def getPubmedEntryDate(elem,pmid):
	pubDateFields = elem.findall('./PubmedData/History/PubMedPubDate')
	allDates = {}
	for pubDateField in pubDateFields:
		assert 'PubStatus' in pubDateField.attrib
		#if 'PubStatus' in pubDateField.attrib and pubDateField.attrib['PubStatus'] == "pubmed":
		pubDateField_Year = pubDateField.find('./Year')
		pubDateField_Month = pubDateField.find('./Month')
		pubDateField_Day = pubDateField.find('./Day')
		pubYear = int(pubDateField_Year.text)
		pubMonth = int(pubDateField_Month.text)
		pubDay = int(pubDateField_Day.text)

		dateType = pubDateField.attrib['PubStatus']
		if pubYear > 1700 and pubYear < 2100:
			allDates[dateType] = (pubYear,pubMonth,pubDay)

	if len(allDates) == 0:
		return None,None,None

	if 'pubmed' in allDates:
		pubYear,pubMonth,pubDay = allDates['pubmed']
	elif 'entrez' in allDates:
		pubYear,pubMonth,pubDay = allDates['entrez']
	elif 'medline' in allDates:
		pubYear,pubMonth,pubDay = allDates['medline']
	else:
		pubYear,pubMonth,pubDay = list(allDates.values())[0]

	return pubYear,pubMonth,pubDay

doiRegex = re.compile(r'^[0-9\.]+\/.+[^\/]$')
def processElem(elem):
	pmidField = elem.find('./MedlineCitation/PMID')
	pmid = pmidField.text

	if not pmid.isdigit():
		return None

	journalYear,journalMonth,journalDay = getJournalDateForMedlineFile(elem,pmid)
	entryYear,entryMonth,entryDay = getPubmedEntryDate(elem,pmid)

	jComparison = tuple ( 9999 if d is None else d for d in [ journalYear,journalMonth,journalDay ] )
	eComparison = tuple ( 9999 if d is None else d for d in [ entryYear,entryMonth,entryDay ] )
	if jComparison < eComparison: # The PubMed entry has been delayed for some reason so let's try the journal data
		pubYear,pubMonth,pubDay = journalYear,journalMonth,journalDay
	else:
		pubYear,pubMonth,pubDay = entryYear,entryMonth,entryDay

	#pubDate = "%d-%02d-%02d" % (pubYear,pubMonth,pubDay)

	# Extract the authors
	authorElems = elem.findall('./MedlineCitation/Article/AuthorList/Author')
	authors = []
	for authorElem in authorElems:
		forename = authorElem.find('./ForeName')
		lastname = authorElem.find('./LastName')
		collectivename = authorElem.find('./CollectiveName')

		name = None
		if forename is not None and lastname is not None and forename.text is not None and lastname.text is not None:
			name = "%s %s" % (forename.text, lastname.text)
		elif lastname is not None and lastname.text is not None:
			name = lastname.text
		elif forename is not None and forename.text is not None:
			name = forename.text
		elif collectivename is not None and collectivename.text is not None:
			name = collectivename.text
		else:
			raise RuntimeError("Unable to find authors in Pubmed citation (PMID=%s)" % pmid)
		authors.append(name)

	mesh = []

	meshElems = elem.findall('./MedlineCitation/MeshHeadingList/MeshHeading')
	for meshElem in meshElems:
		descriptorElem = meshElem.find('./DescriptorName')
		descriptorID = descriptorElem.attrib['UI']
		majorTopicYN = descriptorElem.attrib['MajorTopicYN']
		descriptorName = descriptorElem.text

		thisMesh = [ (descriptorID,descriptorName,majorTopicYN) ]

		qualifierElems = meshElem.findall('./QualifierName')
		for qualifierElem in qualifierElems:
			qualifierID = qualifierElem.attrib['UI']
			majorTopicYN = qualifierElem.attrib['MajorTopicYN']
			qualifierName = qualifierElem.text

			thisMesh.append((qualifierID,qualifierName,majorTopicYN))

		mesh.append(thisMesh)

	chemicals = []
	chemicalElems = elem.findall('./MedlineCitation/ChemicalList/Chemical/NameOfSubstance')
	for chemicalElem in chemicalElems:
		chemID = chemicalElem.attrib['UI']
		chemName = chemicalElem.text
		chemicals.append((chemID,chemName))

	supplementaryConcepts = []
	conceptElems = elem.findall('./MedlineCitation/SupplMeshList/SupplMeshName')
	for conceptElem in conceptElems:
		conceptID = conceptElem.attrib['UI']
		conceptType = conceptElem.attrib['Type']
		conceptName = conceptElem.text
		supplementaryConcepts.append((conceptID,conceptType,conceptName))

	#chemicals = [ (chemID,chemName) for chemID,chemName in chemicals if not chemName in chemicalSkips ]

	titleElems = elem.findall('./MedlineCitation/Article/ArticleTitle')
	titleText = extractTextFromElemList(titleElems)
	if not titleText or all( t is None or t=='' for t in titleText) :
		titleElems = elem.findall('./MedlineCitation/Article/VernacularTitle')
		titleText = extractTextFromElemList(titleElems)
	titleText = [ removeWeirdBracketsFromOldTitles(t) for t in titleText ]
	titleText = [ t for t in titleText if t ]
	titleText = [ html.unescape(t) for t in titleText ]
	titleText = [ removeBracketsWithoutWords(t) for t in titleText ]

	abstractElems = elem.findall('./MedlineCitation/Article/Abstract/AbstractText')
	abstractText = extractTextFromElemList(abstractElems)
	abstractText = [ t for t in abstractText if t ]
	abstractText = [ html.unescape(t) for t in abstractText ]
	abstractText = [ removeBracketsWithoutWords(t) for t in abstractText ]

	referenceCount = None
	if elem.find('./PubmedData/ReferenceList'):
		referenceElems = elem.findall('./PubmedData/ReferenceList/Reference')
		referenceCount = len(referenceElems)
	
	journalTitleElems = elem.findall('./MedlineCitation/Article/Journal/Title')
	journalTitleISOElems = elem.findall('./MedlineCitation/Article/Journal/ISOAbbreviation')
	journalTitle = " ".join( e.text for e in journalTitleElems )
	journalISOTitle = " ".join( e.text for e in journalTitleISOElems )

	doiElems = elem.findall("./PubmedData/ArticleIdList/ArticleId[@IdType='doi']")
	assert len(doiElems) <= 1
	doi = None
	if len(doiElems) == 1 and doiElems[0].text:
		doi = doiElems[0].text
		if not doiRegex.match(doi):
			doi = None

	pmcElems = elem.findall("./PubmedData/ArticleIdList/ArticleId[@IdType='pmc']")
	assert len(pmcElems) <= 1
	pmcid = None
	if len(pmcElems) == 1:
		pmcid = pmcElems[0].text

	pubTypeElems = elem.findall('./MedlineCitation/Article/PublicationTypeList/PublicationType')
	pubType = [ e.text for e in pubTypeElems if not e.text in pubTypeSkips ]

	# Some articles are missing a title
	if len(titleText) == 0:
		return None
	assert len(titleText) == 1, "Unexpected number of titles for PMID:%s. Expected 1, got: %s" % (pmid,titleText)

	article = {}
	article['pubmed_id'] = pmid
	article['pmcid'] = pmcid
	article['doi'] = doi
	article['title'] = titleText[0]
	article['abstract'] = "\n".join(abstractText)
	article['authors'] = authors
	article['chemicals'] = chemicals
	article['mesh'] = mesh
	article['supplementary_concepts'] = supplementaryConcepts
	article['journal'] = journalTitle
	article['journaliso'] = journalISOTitle
	article['publish_year'] = pubYear
	article['publish_month'] = pubMonth
	article['publish_day'] = pubDay
	article['medline_pubtype'] = pubType
	article['reference_count'] = referenceCount
	article['url'] = 'https://www.ncbi.nlm.nih.gov/pubmed/' + pmid

	return pmid,article

def processPubMed(inDir):
	pubmedFiles = sorted( os.path.join(inDir,f) for f in os.listdir(inDir) if f.endswith('.xml.gz') )

	allData = {}
	for pubmedFile in pubmedFiles:
		print(os.path.basename(pubmedFile))
		with gzip.open(pubmedFile,'rt') as f:
			for event, elem in etree.iterparse(f, events=('start', 'end', 'start-ns', 'end-ns')):
				if (event=='end' and elem.tag=='PubmedArticle'):
					result = processElem(elem)
					if result is not None:
						pmid,articleData = result
						allData[pmid] = articleData

					# Important: clear the current element from memory to keep memory usage low
					elem.clear()

	return allData

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Collect all relevant papers into one big file')
	parser.add_argument('--cord19Metadata',required=False,type=str,help='Kaggle CORD-19 metadata file')
	parser.add_argument('--pubmed',required=True,type=str,help='PubMed directory, prefiltered for corona papers')
	parser.add_argument('--pretty', action='store_true',help='Pretty JSON output')
	parser.add_argument('--outFile',required=True,type=str,help='Mega JSON output file')
	args = parser.parse_args()

	assert os.path.isdir(args.pubmed)

	print("Checking file modification dates...")
	previous_output_time = os.path.getmtime(args.outFile) if os.path.isfile(args.outFile) else None
	pubmed_times = [ os.path.getmtime(os.path.join(args.pubmed,filename)) for filename in sorted(os.listdir(args.pubmed)) ]
	cord19_time = [os.path.getmtime(args.cord19Metadata)] if args.cord19Metadata else []
	newest_input = sorted(pubmed_times + cord19_time)[-1]
	if previous_output_time is not None and previous_output_time > newest_input:
		print("Input is older than last output. So no processing is needed!")
		print("Previous output file: %s" % datetime.fromtimestamp(previous_output_time).strftime('%Y-%m-%d %H:%M:%S'))
		print("Newest input file:    %s" % datetime.fromtimestamp(newest_input).strftime('%Y-%m-%d %H:%M:%S'))
		print()
		print("Exiting...")
		sys.exit(0)

	cord19 = []
	if args.cord19Metadata:
		assert os.path.isfile(args.cord19Metadata)
		with open(args.cord19Metadata, newline='') as csvfile:
			csvreader = csv.DictReader(csvfile, delimiter=',', quotechar='"')

			for i,row in enumerate(csvreader):
				cord19.append(row)
				
				
	pubmed = processPubMed(args.pubmed)
	print("Loaded %d from PubMed" % len(pubmed))

	print("Loaded %d from Cord19" % len(cord19))

	defaults = {}
	defaults['cord_uid'] = None
	defaults['pubmed_id'] = None

	combined = list(pubmed.values()) + cord19
	combined = [ {**defaults,**article} for article in combined ]	

	print("Loaded %d in total" % len(combined))

	print("Saving...")
	with gzip.open(args.outFile,'wt') as outF:
		if args.pretty:
			json.dump(combined,outF,indent=2,sort_keys=True)
		else:
			json.dump(combined,outF)

