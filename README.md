# CoronaCentral Machine Learning

This repository contains the code for text mining the coronavirus literature for [CoronaCentral](https://coronacentral.ai). It manages the download, clean up, categorization (using deep learning) and many more steps to process the coronavirus literature. The output of this is then upload to the CoronaCentral website. The web interface of the website is kept in a [separate Github repo](https://github.com/jakelever/corona-web).

This README will cover the three main steps
 - Downloading coronavirus literature
 - Running the full pipeline
 - Uploading to a database
 
## Download the coronavirus literature

Scripts in the [data/](https://github.com/jakelever/corona-ml/tree/master/data) manage the download of the literature from PubMed and CORD-19. These two sources are then combined into one file and fed through the pipeline where they are cleaned up.

## Full Pipeline

The full pipeline in the [pipeline/](https://github.com/jakelever/corona-ml/tree/master/pipeline) directory takes in documents from PubMed and CORD-19 and does cleaning, merging, categorization, and more steps outlined below. These are managed by a Snakemake script.

- Word-lists for entities are sourced from WikiData
- Spotfixes are applied to manually clean up some documents
- Web data is pulled to get metadata tags
- Web data is integrated with the documents and used to infer some article types
- Documents are further cleaned by a number of rules, including steps to normalize journal names
- Documents are parsed and named entity recognition is applied to find mentions of different entities, including viruses
- Categories are predicted using BERT (using scripts in [category_prediction/](https://github.com/jakelever/corona-ml/tree/master/category_prediction))
- Additional categories are identified with rules
- A final filter does some final tidying up and checking
- Document annotations are prepared for upload to a database

## Database

The [database/](https://github.com/jakelever/corona-ml/tree/master/database) directory contains scripts for creating and managing a MySQL database containing documents and annotations.

## Data

If using data from this project, please cite this work along with the CORD-19 dataset.