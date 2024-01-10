# Update

The CoronaCentral data is [available through Zenodo](https://doi.org/10.5281/zenodo.4383289) and no longer available through the web portal.

---

# CoronaCentral Machine Learning

<p>
<a href="https://doi.org/10.5281/zenodo.4383289">
   <img src="https://img.shields.io/badge/data-download-blue.svg" />
</a>
<a href="https://doi.org/10.1073/pnas.2100766118">
   <img src="https://img.shields.io/badge/PNAS-paper-67baea.svg" />
</a>
<a href="https://github.com/jakelever/corona-web">
   <img src="https://img.shields.io/badge/web-code-darkgreen.svg" />
</a>
<a href="https://github.com/jakelever/corona-ml/actions/workflows/pipeline_test.yml">
   <img src="https://github.com/jakelever/corona-ml/actions/workflows/pipeline_test.yml/badge.svg" />
</a>
</p>

This repository contains the code for text mining the coronavirus literature for CoronaCentral. It manages the download, clean up, categorization (using deep learning) and many more steps to process the coronavirus literature. The web interface of the website is kept in a [separate Github repo](https://github.com/jakelever/corona-web).

## Dependencies

This is a Python3 project that relies on several machine learning libraries (e.g. transformers, scikit-learn, etc) and NLP library (e.g. NLTK and spacy). The requirements (including the NLTK stopwords set) can be installed as below: 

```
pip install -r requirements.txt
python -m nltk.downloader stopwords
```

## Running the Pipeline

A good place to start is to run the test run of the core part of the pipeline with the [run_test.sh](https://github.com/jakelever/corona-ml/blob/master/run_test.sh) script (which is run regularly by GitHub to test this repo).

The pipeline, described in detail in the [step by step guide](https://github.com/jakelever/corona-ml/blob/master/stepByStep.md), is run by the master script [coronatime.sh](https://github.com/jakelever/corona-ml/blob/master/coronatime.sh). This requires substantial disk space and time.

## Running the Topic / Article Type Prediction

The core part of the pipeline predicts topics and article types using the title and abstract text of articles. This uses a BERT-based sequence classifier trained using [ktrain](https://github.com/amaiya/ktrain) and [HuggingFace transformers](https://huggingface.co/). The model ([jakelever/coronabert](https://huggingface.co/jakelever/coronabert)) is public and runnable using the transformers library. Below are two Google Colab notebooks with example code for running with transformers or ktrain. 

- [HuggingFace example on Google Colab](https://colab.research.google.com/drive/1cBNgKd4o6FNWwjKXXQQsC_SaX1kOXDa4?usp=sharing)
- [KTrain example on Google Colab](https://colab.research.google.com/drive/1h7oJa2NDjnBEoox0D5vwXrxiCHj3B1kU?usp=sharing)

The method is described in the supplementary materials of the [paper](https://doi.org/10.1073/pnas.2100766118) and detailed performance results can be found in the [machine learning details](https://github.com/jakelever/corona-ml/blob/master/machineLearningDetails.md) document.

## Detailed Step-by-Step Guide

The [stepByStep.md](https://github.com/jakelever/corona-ml/blob/master/stepByStep.md) file contains a detailed guide of all the different steps involved in downloading and processing the documents. A quicker overview is below.

## Quicker Overview

This project follows three main steps
 - Downloading coronavirus literature
 - Running the full pipeline
 - Uploading to a database
 
### Download the coronavirus literature

Scripts in the [data/](https://github.com/jakelever/corona-ml/tree/master/data) manage the download of the literature from [PubMed](https://www.nlm.nih.gov/databases/download/pubmed_medline.html) and [CORD-19](https://www.semanticscholar.org/cord19/download). These two sources are then combined into one file and fed through the pipeline where they are cleaned up.

### Full Pipeline

The full pipeline in the [pipeline/](https://github.com/jakelever/corona-ml/tree/master/pipeline) directory takes in documents from PubMed and CORD-19 and does cleaning, merging, categorization, and more steps outlined below. These are managed by a Snakemake script.

- Word-lists for entities are sourced from WikiData
- Spotfixes are applied to manually clean up some documents
- Web data is pulled to get metadata tags
- Web data is integrated with the documents and used to infer some article types
- Documents are further cleaned by a number of rules, including steps to normalize journal names
- Documents are parsed and named entity recognition is applied to find mentions of different entities, including viruses, drugs, locations, etc
- Categories are predicted using BERT (using scripts in [category_prediction/](https://github.com/jakelever/corona-ml/tree/master/category_prediction))
- Additional categories are identified with rules
- A final filter does some final tidying up and checking
- Document annotations are prepared for upload to a database

### Database

The [database/](https://github.com/jakelever/corona-ml/tree/master/database) directory contains scripts for creating and managing a MySQL database containing documents and annotations.

## Data

The full data is available at [Zenodo](https://doi.org/10.5281/zenodo.4383289). 

## Machine Learning Performance

Detailed information of the parameter tuning, validation results and final test results for the optimal model are provided in the [machine learning details](https://github.com/jakelever/corona-ml/blob/master/machineLearningDetails.md) document.

## Citing

If using the data from the project, it'd be lovely if you'd cite the work. There is currently a [PNAS paper](https://doi.org/10.1073/pnas.2100766118) with bibtex below:

```
@article {coronacentral,
	author = {Lever, Jake and Altman, Russ B.},
	title = {Analyzing the vast coronavirus literature with {C}orona{C}entral},
	volume = {118},
	number = {23},
	elocation-id = {e2100766118},
	year = {2021},
	doi = {10.1073/pnas.2100766118},
	publisher = {National Academy of Sciences},
	issn = {0027-8424},
	URL = {https://www.pnas.org/content/118/23/e2100766118},
	eprint = {https://www.pnas.org/content/118/23/e2100766118.full.pdf},
	journal = {Proceedings of the National Academy of Sciences}
}
```
