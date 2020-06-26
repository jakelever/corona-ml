import argparse
import sys
import xml.etree.cElementTree as etree

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

def filterPubmedFile(inFile,outFile):
	with open(outFile,'w') as outF:
		outF.write('<?xml version="1.0" encoding="utf-8"?>\n')
		outF.write('<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2019//EN" "http://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_190101.dtd">\n')
		outF.write('<PubmedArticleSet>\n')


		for event, elem in etree.iterparse(inFile, events=('start', 'end', 'start-ns', 'end-ns')):
			if (event=='end' and elem.tag=='PubmedArticle'): #MedlineCitation'):
				pmidField = elem.find('./MedlineCitation/PMID')
				pmid = pmidField.text

				hasCoronaDescriptor = False

				meshElems = elem.findall('./MedlineCitation/MeshHeadingList/MeshHeading')
				for meshElem in meshElems:
					descriptorElem = meshElem.find('./DescriptorName')
					descriptorID = descriptorElem.attrib['UI']
					#majorTopicYN = descriptorElem.attrib['MajorTopicYN']
					descriptorName = descriptorElem.text

					isCoronaDescriptor = descriptorID in coronaDescriptors
					if isCoronaDescriptor:
						hasCoronaDescriptor = True

						hasQualifiers = False
						qualifierElems = meshElem.findall('./QualifierName')
						for qualifierElem in qualifierElems:
							qualifierID = qualifierElem.attrib['UI']
							#majorTopicYN = qualifierElem.attrib['MajorTopicYN']
							qualifierName = qualifierElem.text
							hasQualifiers = True
							
							print("\t".join([pmid,descriptorName,qualifierName,descriptorID,qualifierID]))

						if not hasQualifiers:
							print("\t".join([pmid,descriptorName,"",descriptorID,""]))

				#print(dir(elem))
				#print(elem.text)
				#print(etree.tostring(elem))
				#assert False

				if hasCoronaDescriptor:
					#print(pmid)
					outF.write(etree.tostring(elem).decode("utf-8"))

				# Important: clear the current element from memory to keep memory usage low
				elem.clear()
		outF.write('</PubmedArticleSet>\n')

			
inFile = sys.argv[1]
outFile = sys.argv[2]
#print(inFile, outFile)
filterPubmedFile(inFile, outFile)

#if __name__ == '__main__':
#	parser = argparse
