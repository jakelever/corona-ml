# Machine Learning Details

A supervised learning approach was used to predict topics and article types. The dataset is available as the [annotated_documents.json.gz](https://github.com/jakelever/corona-ml/blob/master/category_prediction/annotated_documents.json.gz) archive. It was split into training, validation and test sets. Hyperparameter optimization was used to test different BERT models as well as traditional approaches and the performance was evaluated on the validation set. The best model was then evaluated on the held-out test set and the performance reported. This document lists the parameters and models that were evaluated. The best performance for each classifier / BERT model on the validation set. Finally, the table at the bottom shows the performance for each label (topic or article type) on the validation set with the best model from the validation test.

## Hyperparameter Tuning

A grid search was used to test different models and parameters for the different approaches. The table below lists the hyperparameters tested for the BERT-based, Logistic Regression, Linear SVC and RandomForests classifiers.

| Classifier                                          | Parameter                    | Options                                                                                                                                                                                                                       |
|-----------------------------------------------------|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| BERT                                                | Epochs                       | 4, 8, 12, 16, 24, 32, 48, 64, 80, 96                                                                                                                                                                                          |
| BERT                                                | Learning Rate                | 1e-3, 5e-4, 1e-4, 5e-5, 1e-5, 5e-6                                                                                                                                                                                            |
| BERT                                                | Model                        | BlueBert, dmis-lab/biobert-v1.1,   microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext,   microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract,   allenai/scibert_scivocab_uncased, allenai/scibert_scivocab_cased' |
| Logistic Regression / Linear SVC / Random   Forests | SVD Dimensionality Reduction | None, 8, 16, 32, 64, 128                                                                                                                                                                                                      |
| Logistic Regression / Linear SVC                    | C                            | 0.1, 1, 10, 20                                                                                                                                                                                                                |
| Random Forests                                      | No of Estimators             | 50, 100, 200                                                                                                                                                                                                                  |

## Results of different ML methods for validation set

Different methods, including different BERT models and traditional approaches, were compared by training the training set and evaluating on the validation set. Below is the best performance for each method/model 

| Method / BERT Model                                           | Macro Precision | Macro Recall | Macro F1 | Optimal Parameters                     |
|---------------------------------------------------------------|-----------------|--------------|----------|----------------------------------------|
| microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract          | 0.805           | 0.76         | 0.774    | epochs = 32, learning_rate = 5e-05     |
| allenai/scibert_scivocab_cased                                | 0.797           | 0.749        | 0.765    | epochs = 32, learning_rate = 5e-05     |
| allenai/scibert_scivocab_uncased                              | 0.774           | 0.762        | 0.763    | epochs = 96, learning_rate = 5e-05     |
| microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext | 0.802           | 0.741        | 0.762    | epochs = 32, learning_rate = 5e-05     |
| dmis-lab/biobert-v1.1                                         | 0.791           | 0.734        | 0.757    | epochs = 32, learning_rate = 5e-05     |
| bluebert/base_uncased_pubmedANDmimicIII                       | 0.754           | 0.704        | 0.715    | epochs = 32, learning_rate = 0.0001    |
| LogisticRegression                                            | 0.721           | 0.543        | 0.603    | C = 10, svd_reduction = None           |
| LinearSVC                                                     | 0.683           | 0.554        | 0.592    | C = 0.1, svd_reduction = None          |
| RandomForestClassifier                                        | 0.676           | 0.194        | 0.28     | n_estimators = 50, svd_reduction = 128 |

## Performance Breakdown by Topic / Article Type

Below is the table outlining performance for the different topics and article types. Some of the poorer performing labels are likely challenged by the small number of papers in the test set. For example, the Long Haul category has terrible performance, but manual review of the tagged papers at https://coronacentral.ai/longhaul show that the classifier does identify Long Haul papers well.

| Topic/Article Type            | Precision | Recall | F1   |
|-------------------------------|-----------|--------|------|
| Clinical Reports              | 0.84      | 0.63   | 0.72 |
| Comment/Editorial             | 0.73      | 0.69   | 0.71 |
| Communication                 | 0.5       | 0.25   | 0.33 |
| Contact Tracing               | 1         | 1      | 1    |
| Diagnostics                   | 0.93      | 0.83   | 0.88 |
| Drug Targets                  | 0.67      | 0.5    | 0.57 |
| Education                     | 0.63      | 0.71   | 0.67 |
| Effect on Medical Specialties | 0.79      | 0.49   | 0.61 |
| Forecasting & Modelling       | 1         | 0.88   | 0.93 |
| Health Policy                 | 0.5       | 0.32   | 0.39 |
| Healthcare Workers            | 0.8       | 0.89   | 0.84 |
| Imaging                       | 0.93      | 0.72   | 0.81 |
| Immunology                    | 0.44      | 0.44   | 0.44 |
| Inequality                    | 0.83      | 0.71   | 0.77 |
| Infection Reports             | 0.75      | 0.3    | 0.43 |
| Long Haul                     | 0         | 0      | 0    |
| Medical Devices               | 0.71      | 0.63   | 0.67 |
| Meta-analysis                 | 0.75      | 0.86   | 0.8  |
| Misinformation                | 1         | 0.67   | 0.8  |
| Model Systems & Tools         | 1         | 0.2    | 0.33 |
| Molecular Biology             | 0.72      | 0.68   | 0.7  |
| News                          | 0.5       | 0.4    | 0.44 |
| Non-human                     | 0.83      | 0.5    | 0.63 |
| Non-medical                   | 1         | 0.43   | 0.61 |
| Pediatrics                    | 0.79      | 0.79   | 0.79 |
| Prevalence                    | 1         | 0.56   | 0.71 |
| Prevention                    | 0.72      | 0.56   | 0.63 |
| Psychology                    | 1         | 0.64   | 0.78 |
| Recommendations               | 0.7       | 0.54   | 0.61 |
| Review                        | 0.57      | 0.75   | 0.65 |
| Risk Factors                  | 0.65      | 0.51   | 0.57 |
| Surveillance                  | 1         | 0.5    | 0.67 |
| Therapeutics                  | 0.7       | 0.68   | 0.69 |
| Transmission                  | 0.75      | 0.75   | 0.75 |
| Vaccines                      | 1         | 0.33   | 0.5  |
| MICRO                         | 0.76      | 0.62   | 0.68 |
| MACRO                         | 0.76      | 0.58   | 0.64 |
