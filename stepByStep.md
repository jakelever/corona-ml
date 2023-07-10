# Step-by-step guide to CoronaCentral processing pipeline

This documents describes on fine detail the steps involved to get the coronavirus papers, predict topics and article types, do cleaning and lots of other steps. The code for most of these steps are in the [pipeline/](https://github.com/jakelever/corona-ml/tree/master/pipeline/) directory. The master script [coronatime.sh](https://github.com/jakelever/corona-ml/blob/master/coronatime.sh) runs the data download, the Snakemake pipeline script and then additional steps for upload and tweeting.

## Requirements

This is a Python3 project and the package requirements are listed in the requirements.txt file. These include spacy, a scispacy model and ktrain that uses huggingface transformers. The requirements can be installed by pip using:

```sh
pip install -r requirements.txt
```

One step also uses nltk and the stopwords dataset. It should be installed by using:

```sh
python -m nltk.downloader stopwords
```

## Downloading the data

The first step downloads the [CORD-19](https://www.semanticscholar.org/cord19) dataset along with PubMed filtered for coronavirus articles. These scripts are stored in the data/ directory. The [run_update.sh](https://github.com/jakelever/corona-ml/blob/master/data/run_update.sh) scripts runs the different parts that are described below.

### PubMed

The FTP listing of [PubMed files](https://www.nlm.nih.gov/databases/download/pubmed_medline.html) is updated with the [updatePubmedListing.sh](https://github.com/jakelever/corona-ml/blob/master/data/updatePubmedListing.sh) file. PubMed is distributed as a large set of XML files with regular updates of individual XML files that contain new articles or updates to existing articles. [Snakemake](https://github.com/jakelever/corona-ml/blob/master/data/Snakefile) is used to run [downloadAndProcessPubmedFile.sh](https://github.com/jakelever/corona-ml/blob/master/data/downloadAndProcessPubmedFile.sh) on any new PubMed files. This script fetches the appropriate URL from the FTP listing for the PubMed file, downloads the file and executes [filterPubMedForCoronaPapersByKeyword.py](https://github.com/jakelever/corona-ml/blob/master/data/filterPubMedForCoronaPapersByKeyword.py) to filter for documents that appear to be coronavirus related. This script does fairly relaxed filtering. Later filtering (at the filterForVirusDocs.py stage) is more strict and requires a specific mention of a relevant coronavirus. This relaxed filtering is done as later steps may make updates to the title and abstract (through document merges, manual corrections or pulling metadata from publishers' websites). The filtering requirements are:

- Contain a mention of a relevant coronavirus (using the custom set of coronavirus synonyms for SARS-CoV-2, MERS-CoV and SARS-CoV available in the terms_viruses.json file)
- Have a relevant MeSH heading (e.g. D045473:SARS Virus)
- Have a relevant supplementary MeSH heading (e.g. C000657245:COVID-19)
- Mention the word coronavirus and be published from 2019 onwards

### CORD-19

The [downloadCORD19_metadataOnly.sh](https://github.com/jakelever/corona-ml/blob/master/data/downloadCORD19_metadataOnly.sh) script manages the [CORD-19](https://www.semanticscholar.org/cord19) download. The URL of the latest CORD-19 dataset is fetched from the [CORD-19 releases page](https://ai2-semanticscholar-cord-19.s3-us-west-2.amazonaws.com/historical_releases.html). The filename, which contains a date, is checked to see if it is newer than a previously downloaded version. If a new version is found, it is downloaded and only the metadata.csv file is extracted. The CSV file contains fields for the title, abstract and various identifiers. The full-text data is not used from CORD-19.

### Combining PubMed and CORD-19

The [collectAllPapers.py](https://github.com/jakelever/corona-ml/blob/master/data/collectAllPapers.py) script converts the CORD-19 metadata file and PubMed XML files into a JSON format containing the needed fields (e.g. title, abstract and identifiers). No merging is done at this stage so there are many duplicate documents, as well as many documents that are not actually relevant for SARS-CoV-2, MERS-CoV or SARS-CoV. No filtering is done on the CORD-19 dataset yet. The PubMed conversion uses approaches developed for the [BioText](https://github.com/jakelever/biotext) project and does some minor cleaning to titles and text. This includes removing square brackets from around some article titles, cleaning publication date information and removing and fixing some Unicode characters. The collectAllPapers.py script will do some quick checks on file modification dates to make sure it's not doing unnecessary work.

## Wordlist generation

To provide more intelligent search functionality, mentions in the title or abstract of important biomedical concepts are normalized back to WikiData terms (where possible). This means that a search for a drug provides papers that mention any of the synonyms known for it. To create the various wordlists of synonyms for all the biomedical concepts, a set of scripts (in the pipeline/ directory) are used  to pull information from WikiData.

- [getDrugsFromWikidata.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/getDrugsFromWikidata.py) - Pulls drug names (concepts that are instances of [medication](https://www.wikidata.org/wiki/Q12140))
- [getGenesFromWikidata.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/getGenesFromWikidata.py) - Pulls human gene/protein names
- [getGeonamesFromWikidata.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/getGeonamesFromWikidata.py) - Pulls locations including countries, cities and some smaller regions.
- [getMedicalDisciplinesFromWikidata.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/getMedicalDisciplinesFromWikidata.py) - Pulls medicial disciplines/specialties (concepts that are instances of [medical specialty](https://www.wikidata.org/wiki/Q930752))
- [getSymptomsFromWikidata.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/getSymptomsFromWikidata.py) - Pulls symptoms (concepts that are instances or subclasses of [symptom](https://www.wikidata.org/wiki/Q169872)

To capture mentions of important coronavirus proteins, the [getCoronavirusProteins.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/getCoronavirusProteins.py) generates a custom set of synonyms for the various coronavirus proteins in SARS-CoV-2, MERS-CoV and SARS-CoV. It creates a list of unambigious terms (e.g. MERS-CoV spike protein) and ambiguous terms (e.g. spike protein) that can be disambiguated later given mentions of specific viruses in the same document.

The [predefined/](https://github.com/jakelever/corona-ml/tree/master/pipeline/predefined/) directory contains custom manually-curated lists of different entity types. The [terms_viruses.json](https://github.com/jakelever/corona-ml/blob/master/pipeline/predefined/terms_viruses.json) file contains synonyms for the three coronaviruses (and associated diseases). The [more_custom.tsv](https://github.com/jakelever/corona-ml/blob/master/pipeline/predefined/more_custom.tsv) contains a list of curated terms of the different entity types. The getCustomTerms.py script is used to expand this list by pulling synonyms from Wikidata using the provided WikiData IDs and combined with the terms_custom.json data already in the JSON format. The [removals.tsv](https://github.com/jakelever/corona-ml/blob/master/pipeline/predefined/removals.tsv) contains a list of synonyms to remove. This file is used later in the named entity recognition stage.

## Processing the data

The input to the pipeline is the merged documents from CORD-19 and PubMed. These contain a lot of duplicates and irrelevant documents as well as lots of smaller errors. This large JSON file is copied to pipeline/data/alldocuments.json. The Snakemake script is then execute to run all the stages below.

This pipeline will take over 12 hours to run if run from scratch. The lengthy scripts will check for previous runs and try to skip unnecessary re-processing of scripts. The particularly time-consuming scripts are scrapeWebdata.py, filterOutLanguages.py, doNER.py, extractGeneticVariationAndLineages.py and applyCategoryModel.py. The runtime for an update is closer to one hour.

### Applying spotfixes and adding hand-coded documents ([applySpotfixesAndAddCustomDocs.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/applySpotfixesAndAddCustomDocs.py))

Some manual fixes to documents (stored in spotFixes.json) are applied to the corpus and any extra documents are added from additions.json. This allows the addition of documents not captured by CORD-19 or PubMed.

### Scrape web data ([scrapeWebdata.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/scrapeWebdata.py))

Information from the publisher's website provides valuable information about the article type of each document. This script will retrieve the HTML page from the publishers website and identify relevant metadata using [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) for parsing. It will try all URLs associated with a document excluding PubMed and URLs ending with '.pdf'. It will then find <meta> tags or <span> tags with predefined classes that identify metadata for the article (e.g. 'article-header__journal'). This data is stored separately from the documents.

### Integrate web data ([integrateWebData.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/integrateWebData.py))

The metadata from publishers' website needs to be integrated with each document. The crawled <meta> and <span> tags are search for those likely containing article type information and matched against a manually-curated list of frequent terms for article types to map it to the CoronaCentral defined article types. For instance a <meta> tag that gives "DC.Subject" as "review-article" is mapped to the Review article type. PubMed flags (e.g. Editorial) are also used to map to article types. Obvious keywords in the title (e.g. Retracted) are also used for some article types. This article type information is stored as the inferred_article_type field for those documents for which data is available and is integrated in a later step.

The web data is also used to clean up journal names. A mapping is created from journal names found in CORD-19 and PubMed to journal names provided by publication  websites. For example, "N Engl J Med" in PubMed is mapped to "New England Journal of Medicine". This provides for more standardized journal naming.

### Clean up documents ([cleanupDocs.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/cleanupDocs.py))

The cleanup stage applies a number of small fixes described below to all documents:

- Unicode dash characters are converted to hyphens
- Common phrasing for missing abstracts (e.g. 'no abstract is available for this article') are replaced by an actually empty abstract
- Unnecessary prefixes on titles are trimmed (e.g. 'full-length title')
- Unnecessary prefixes on abstracts are trimmed (e.g. 'unlabelled abstract')
- Copyright phrases in abstracts are removed
- Preprint journal names are standardized (e.g. 'biorxiv.org' to 'bioRxiv')
- Titles that have empty parentheses at the end are trimmed
- Some structured abstract section headings are cleaned to add necessary spaces (e.g. "RESULTS:We did" to "RESULTS: We did")
- Publication date fields are standardized so that year, month and day is stored separately

### Merge duplicate documents ([mergeDuplicates.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/mergeDuplicates.py))

CORD-19 is a combination of multiple sources and contains duplicate documents. We combine PubMed as well which introduces more duplicates. This stage uses some fields to resolve duplicate documents and merge groups of documents into one document while maintaining appropriate metadata.

It will try to merge documents with the following field options:
- DOI alone
- PubMed ID alone
- CORD-19 identifier (cord_uid) alone
- Publish year, title and authors
- Publish year, title and abstract
- Publish year, title and journal

Groups of documents that should be merged are found using these field matches. Documents are then merged, with preference for information coming from non-preprint documents. The most complete publication date is also selected (so year, month and day if possible). This stage also removes any documents flagged as Erratum.

### Filter out non-English language documents ([filterOutLanguages.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/filterOutLanguages.py))

Unfortunately this resource is limited to English language research articles. We remove non-English language articles using heuristics on frequency of stopwords from different languages. The stopwords are loaded from NLTK. The languages checked using stopwords are: Arabic, Azerbaijani, Danish, Dutch, Finnish, French, German, Greek, Hungarian, Indonesian, Italian, Kazakh, Nepali, Norwegian, Portuguese, Romanian, Russian, Slovene, Spanish, Swedish, Tajik and Turkish. If 5 or more stopwords were found from a non-English language then the article is flagged. This cutoff was found to provide a good accuracy for identifying non-English articles. Non-english stopwords were filtered for English stopwords and the words: 'se','sera','et'. Documents containing Chinese, Japanese or Korean characters are also flagged.

### Integrate manual annotations ([integrateAnnotations.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/integrateAnnotations.py))

At this stage, we integrate the annotations used for the training set for topics and article types. These are contained in the annotations.json.gz archive (which needs to be ungzipped). The annotations match documents by their DOI or PubMed identifiers and include manual curation of topic and article type. These annotations were achieved through the manual annotation system that is available in the annotation/ directory.

### Extract mentions of drugs, locations, symptoms, etc ([doNER.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/doNER.py))

Using the wordlists outlined above, we now find mentions of important biomedical concepts in the title and abstracts and saved this information. This script loads up all the different entity listing files and uses [Kindred](https://github.com/jakelever/kindred)'s entity recognition system to flag mentions of them in articles. This approach uses exact string matching with knowledge of word boundaries to find the longest mapping entities in documents. This means that in the sentence: "We studied the EGF receptor", "EGF receptor" would be identified as a gene/protein, and "EGF" would not be identified as it is contained within a larger entity. The location of entities along with their normalized identifier (normally the WikiData identifier) are stored in the document.

The script uses publication years to trim mentions of the different viruses so no papers before 2002 can contains 'SARS-CoV', none before 2012 contain 'MERS-CoV' and none before 2019 contain 'SARS-CoV-2'.

This script also does some disambiguation for viral protein mentions. For papers that discuss a single virus type, and mention a viral protein ambiguously (e.g. spike protein), it is inferred that the mention is for the protein of the corresponding virus. If multiple viruses are mention, no disambiguation is done. 

This script also makes use of the the removals.tsv list to remove some uncommon and tricky synonyms. The conflicting entity type also provides a means to reduce poorly normalized terms (e.g. 'Edinburgh Postpartum Depression Scale' stops the word Edinburgh mapping to the location when that phrase is used). Finally, entities that cannot be unambigiously mapped are discarded.

### Filter for only documents that mention relevant viruses ([filterForVirusDocs.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/filterForVirusDocs.py))

After the named recognition stage, the documents contain the entities field which lists mentions of the important biomedical concepts. One of these is viruses. This stage filters for documents that contain a mention of a virus.

### Extract mentions of genetic variation and viral lineages ([extractGeneticVariationAndLineages.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/extractGeneticVariationAndLineages.py))

This script uses a large set of regular expressions to find mentions of genomic variation and viral lineages. The genomic variation work reuses a system built for normalizing some PubTator mutations for the [PGxMine project](https://github.com/jakelever/pgxmine).

For genomic variations, there are a large set of example phrasings that are mapped to regular expressions. For example, 'THREONINE-to-METHIONINE mutation at residue 790' provide a phrasing for a protein modification. Parts of the phrasing are mapped to regular expressions (e.g. THREONINE to an amino acid regular expression). These are then used to normalize to the [HGVS standard](https://varnomen.hgvs.org/). Some stopwords, available in the geneticvariation_stopwords.txt file, are used to remove common false positives from this method.

Viral lineages are also identified with a set of regular expressions. The main one is '\b[ABCP]\.\d\d?(\.\d+)\*\.?\b' which captures lineages named that start with ABCP and have numeric sub-numberings, e.g. B.1.1.7. Other regular expressions are used for a few other formats and a small set of curated synonyms are used to map lineages, e.g. '501Y.V1' to 'B.1.1.7 (UK)'.

### Predict topics and article types using a BERT model ([applyCategoryModelFromHuggingFace.py](https://github.com/jakelever/corona-ml/blob/master/category_prediction/applyCategoryModelFromHuggingFace.py))

The main intense machine learning is dealt with by the applyCategoryModelFromHuggingFace.py script. At this point, topics and article types are combined together as "categories". The scripts for training, evaluating and running the machine learning models are in the separate [category_prediction/](https://github.com/jakelever/corona-ml/tree/master/category_prediction) directory. The applyCategoryModelFromHuggingFace.py loads a pretrained model for topic and article type prediction. This model uses [ktrain](https://github.com/amaiya/ktrain). It is a BERT-based multi-label document classifier using the [jakelever/coronabert](https://huggingface.co/jakelever/coronabert) model. This model is fine-tuned from the [microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract](https://huggingface.co/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract) model. As input, it takes the title and abstract text. Below are two Colab example notebooks showing how to use this model in HuggingFace and ktrain.

- [HuggingFace example on Google Colab](https://colab.research.google.com/drive/1cBNgKd4o6FNWwjKXXQQsC_SaX1kOXDa4?usp=sharing)
- [KTrain example on Google Colab](https://colab.research.google.com/drive/1h7oJa2NDjnBEoox0D5vwXrxiCHj3B1kU?usp=sharing)

### Predict several additional topics/article types using hand-coded rules ([doExtraCategories.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/doExtraCategories.py))

Some heuristics, outlined below, are then employed to identify more topics and article types.

- The Clinical Trials topic, which was not predicted by the BERT classifier, is identified using regular expressions for clinicial trial identifiers (e.g. NCT123456 or CTR123456).
- If the journal is 'MMWR. Morbidity and Mortality Weekly Report', the article type is assigned to CDC Weekly Report
- Papers that are flagged as Meta-analysis and Reviews are changed to just Meta-analysis
- If an article type was inferred from web data, it overwrites any article types currently assigned to the article.
- Finally any article without an assigned article type is annotated as a Research article.

### Separate categories in topics and article types ([separateArticleTypesAndTopics.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/separateArticleTypesAndTopics.py))

This splits the categories predicted by BERT and hand-coded rules into two separate fields. A list of article types is used to divide the categories appropriately.

### Do some final filtering and cleaning ([finalFilter.py](https://github.com/jakelever/corona-ml/blob/master/pipeline/finalFilter.py))

Some final filtering steps are applied to the data as outlined below:

- Documents without a URL, or identifier that could derive a URL (e.g. DOI or PubMed ID) are removed
- Documents that were manually flagged as Not Relevant or to be removed from corpus are removed from the corpus
- To reduce filesizes, associated webdata is removed from documents

### Gzip for completion

The final step for the CoronaCentral corpus file is gzipping up the coronacentral.json file.

### Get Altmetric data ([getAltmetricData.py](https://github.com/jakelever/corona-ml/blob/master/altmetric/getAltmetricData.py))

The Altmetric API will be polled for the score data for the documents in the corpus. This is stored as a separate file and used for the web server to prioritize tables.

## Database Upload

Once the CoronaCentral corpus is prepared, it needs to be uploaded to the database of the web server so the website can be rebuilt with updated data. The scripts in the [database/](https://github.com/jakelever/corona-ml/tree/master/database) directory manage this with the [reload_db.sh](https://github.com/jakelever/corona-ml/blob/master/database/reload_db.sh) master script managing the individual steps outlined below.

- [createDB.py](https://github.com/jakelever/corona-ml/blob/master/database/createDB.py): Building the database structure - for simplicity the database is dropped and everything is rebuilt
- [loadDocsAndAnnotations.py](https://github.com/jakelever/corona-ml/blob/master/database/loadDocsAndAnnotations.py): Load the corpus with topic, article type and entity annotations
- [loadAltmetricData.py](https://github.com/jakelever/corona-ml/blob/master/database/loadAltmetricData.py): Load the Altmetric data in for the documents
- [loadLocationCoordinates.py](https://github.com/jakelever/corona-ml/blob/master/database/loadLocationCoordinates.py): Load the latitude and longitude coordinates in for geographic locations. This is used for the mapping functionality
- [cleanupDB.py](https://github.com/jakelever/corona-ml/blob/master/database/cleanupDB.py): Do some database cleaning to make sure there aren't any unused entity types or entities

## Additional Steps

The update script will then direct the NodeJS web server to do a rebuild with the new database contents. The web server code is available at https://github.com/jakelever/corona-web.

The regular update script will then potentially do the two following things:
- Upload the corpus to [Zenodo](https://doi.org/10.5281/zenodo.4383289) once a week

