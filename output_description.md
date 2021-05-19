This describes the output file for the [CoronaCentral](https://coronacentral.ai) data. The scripts used to create it are hosted in the [corona-ml](https://github.com/jakelever/corona-ml) Github repo. The sources for the documents before processing for CoronaCentral are [PubMed](https://www.nlm.nih.gov/databases/download/pubmed_medline.html) and [CORD-19](https://www.semanticscholar.org/cord19/download).

The file is a gzipped JSON document containing one record per document. Each document has at least one of: a PubMed ID, a CORD-19 ID (cord_uid), a DOI or a URL.

The fields that documents should have are:

* pubmed\_id: PubMed identifier (optional)
* pmcid: PubMed Central identifier (optional)
* doi: Digital object identifier (optional)
* cord\_uid: CORD-19 identifier (optional)
* url: URL
* journal: Journal/preprint server
* publish\_year: Year of publication (optional)
* publish\_month: Month of publication (optional)
* publish\_day: Day of publication (optional)
* title: Title of article
* abstract: Abstract of article (optional)
* is\_preprint: Whether the article is a preprint
* topics: Predicted topics for article
* articletypes: Predicted article types for article
* entities: Extracted entities (e.g. drugs) with identifiers and locations within text

Please report issues to the [corona-ml Github issues page](https://github.com/jakelever/corona-ml/issues).

