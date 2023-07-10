import argparse
import json
import xml.etree.cElementTree as etree
import html
import re
import calendar
import unicodedata
import sys

import tempfile
import hashlib

import shutil
import urllib.request as request
from contextlib import closing
import time
import gzip
import traceback

coronaDescriptors = {}
coronaDescriptors['D018352'] = 'Coronavirus Infections'
coronaDescriptors['D065207'] = 'Middle East Respiratory Syndrome Coronavirus'
coronaDescriptors['D000073640'] = 'Betacoronavirus'
coronaDescriptors['D018352'] = 'Coronavirus Infections'
coronaDescriptors['D045473'] = 'SARS Virus'
coronaDescriptors['D045169'] = 'Severe Acute Respiratory Syndrome'
coronaDescriptors['D000073641'] = 'Betacoronavirus 1'
coronaDescriptors['D017941'] = 'Coronavirus, Rat'
coronaDescriptors['D006517'] = 'Murine hepatitis virus'

covidSuppDescriptors = {}
covidSuppDescriptors['C000657245'] = 'COVID-19'
covidSuppDescriptors['C000656484'] = 'severe acute respiratory syndrome coronavirus 2'

def download_file(url,local_filehandle):
	with closing(request.urlopen(url)) as r:
		shutil.copyfileobj(r, local_filehandle)

def download_file_and_check_md5sum(url, local_filehandle):
	with tempfile.NamedTemporaryFile() as tf:
		md5_url = "%s.md5" % url
		download_file(md5_url, tf.file)
		
		tf.file.seek(0)
		expected_md5 = tf.file.read().decode().strip()
		assert expected_md5.startswith('MD5(') and '=' in expected_md5
		expected_md5 = expected_md5.split('=')[1].strip()
		#print("expected:", expected_md5)

	download_file(url, local_filehandle)
	local_filehandle.seek(0)
	got_md5 = hashlib.md5(local_filehandle.read()).hexdigest()
	#print("got:", got_md5)

	if expected_md5 != got_md5:
		raise RuntimeError("MD5 of downloaded file doesn't match expected: %s != %s" % (expected_md5,got_md5))

def download_file_with_retries(url, local_filehandle, check_md5=False, retries=10):
	for tryno in range(retries):
		try:
			if check_md5:
				download_file_and_check_md5sum(url, local_filehandle)
			else:
				download_file(url,local_filehandle)
			return
		except:
			print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])
			traceback.print_exc()
			time.sleep(5*(tryno+1))

	raise RuntimeError("Unable to download %s" % url)

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

# XML elements to separate text between
separationList = ['title', 'p', 'sec', 'break', 'def-item', 'list-item', 'caption']
def filterPubmedFile(inFile,virusKeywordFile,outFile):
	with open(virusKeywordFile) as f:
		virusKeywordData = json.load(f)
		#sarscov2Keywords = []
	coronaKeywords = []
	for wikidataID,virus in virusKeywordData.items():
		#if virus['name'] == 'SARS-CoV-2':
		#	sarscov2Keywords.append(virus['name'])
		#	sarscov2Keywords += virus['aliases']
		coronaKeywords.append(virus['name'])
		coronaKeywords += virus['aliases']
	
	# Too non-specific, so will rely on MeSH terms
	skipKeywords = ['sars','mers']
	coronaKeywords = [ k for k in coronaKeywords if k not in skipKeywords ]

	#sarscov2Keywords = sorted(set( vk.strip().lower() for vk in sarscov2Keywords))
	coronaKeywords = sorted(set( k.strip().lower() for k in coronaKeywords))

	coronaRegexes = [ re.compile(r'\b%s\b' % k, flags=re.IGNORECASE) for k in coronaKeywords ]

	with open(outFile,'w') as outF:
		outF.write('<?xml version="1.0" encoding="utf-8"?>\n')
		outF.write('<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2019//EN" "http://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_190101.dtd">\n')
		outF.write('<PubmedArticleSet>\n')


		for event, elem in etree.iterparse(inFile, events=('start', 'end', 'start-ns', 'end-ns')):
			if (event=='end' and elem.tag=='PubmedArticle'): #MedlineCitation'):
				pmidField = elem.find('./MedlineCitation/PMID')
				pmid = pmidField.text

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

				combinedText_lower = "\n".join(titleText + abstractText).lower()


				journalYear,journalMonth,journalDay = getJournalDateForMedlineFile(elem,pmid)
				entryYear,entryMonth,entryDay = getPubmedEntryDate(elem,pmid)

				jComparison = tuple ( 9999 if d is None else d for d in [ journalYear,journalMonth,journalDay ] )
				eComparison = tuple ( 9999 if d is None else d for d in [ entryYear,entryMonth,entryDay ] )
				if jComparison < eComparison: # The PubMed entry has been delayed for some reason so let's try the journal data
					pubYear,pubMonth,pubDay = journalYear,journalMonth,journalDay
				else:
					pubYear,pubMonth,pubDay = entryYear,entryMonth,entryDay

				isCoronaPaper = False

				if pubYear and int(pubYear) >= 2019 and 'coronavirus' in combinedText_lower:
					isCoronaPaper = True

				if any( keyword in combinedText_lower for keyword in coronaKeywords ):
					#print("COVID_KEYWORD\t%s" % pmid)
					if any (regex.search(combinedText_lower) for regex in coronaRegexes):
						isCoronaPaper = True

				meshElems = elem.findall('./MedlineCitation/MeshHeadingList/MeshHeading')
				for meshElem in meshElems:
					descriptorElem = meshElem.find('./DescriptorName')
					descriptorID = descriptorElem.attrib['UI']
					#majorTopicYN = descriptorElem.attrib['MajorTopicYN']
					descriptorName = descriptorElem.text

					isCoronaDescriptor = descriptorID in coronaDescriptors
					if isCoronaDescriptor:
						isCoronaPaper = True

				suppMeshElems = elem.findall('./MedlineCitation/SupplMeshList/SupplMeshName')
				for suppMeshElem in suppMeshElems:
					descriptorID = suppMeshElem.attrib['UI']
					descriptorName = suppMeshElem.text

					if descriptorID in covidSuppDescriptors:
						#print("COVID_SUPPMESH\t%s" % pmid)
						isCoronaPaper = True
					

				if isCoronaPaper:
					outF.write(etree.tostring(elem).decode("utf-8"))

				# Important: clear the current element from memory to keep memory usage low
				elem.clear()
		outF.write('</PubmedArticleSet>\n')

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Filter a PubMed file for papers that discuss coronavirus (SARS/MERS/COVID)")
	parser.add_argument('--inURL',required=True,type=str,help='Input PubMed file URL on FTP')
	parser.add_argument('--virusKeywords',required=True,type=str,help='Input JSON file')
	parser.add_argument('--outFile',required=True,type=str,help='Output filtered PubMed file')
	args = parser.parse_args()

	with tempfile.NamedTemporaryFile() as tf_pubmed_gz, tempfile.NamedTemporaryFile() as tf_pubmed:
		print("Downloading...")
		download_file_with_retries(args.inURL, tf_pubmed_gz.file, check_md5=True)
				
		tf_pubmed_gz.file.seek(0)
		gzippedFile = gzip.GzipFile(fileobj=tf_pubmed_gz.file)
			
		print("Filtering Pubmed file...")
		filterPubmedFile(gzippedFile, args.virusKeywords, args.outFile)
		
		print("Done.")
