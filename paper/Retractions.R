
library(ggplot2)
library(plyr)

data <- read.table('data/retractions.txt',sep='\t',quote='')
colnames(data) <- c('pmid','year','month','day','has_retraction_flag','has_retraction_in_title','is_sarscov2_paper','is_preprint','title')
data <- data[!duplicated(data$pmid),]

data$has_retraction_flag <- data$has_retraction_flag == 'True'
data$has_retraction_in_title <- data$has_retraction_in_title == 'True'
data$is_sarscov2_paper <- data$is_sarscov2_paper == 'True'
data$is_preprint <- data$is_preprint == 'True'

data <- data[order(data$year,data$month,data$day),]

by_year <- plyr::count(data$year)

ggplot(data=by_year[by_year$x>=2000,], aes(x=x, y=freq)) +
  geom_bar(stat="identity") +
  labs(title='Retractions in PubMed', y = "# of retractions", x = "Year")

sarscov2_retractions <- data[data$is_sarscov2_paper,]

#comparable <- data[which(data$is_sarscov2_paper)[1]:nrow(data),]
comparable <- data[data$year==2020 & data$month >= 2,]

plyr::count(comparable$is_sarscov2_paper)

#papers_after_first_sarscov2 <- data[data$year==2020 &&]

rateDataWithType = read.table('data/publicationRateWithMore.tsv')
colnames(rateDataWithType) <- c('count','year','month','paperType')

sarscov2_retracted_count <- sum(comparable$is_sarscov2_paper)
other_retracted_count <- nrow(comparable) - sarscov2_retracted_count

sarscov2_count <- sum(rateDataWithType[rateDataWithType$year==2020 & rateDataWithType$month >= 2 & rateDataWithType$paperType == 'corona','count'])
other_count <- sum(rateDataWithType[rateDataWithType$year==2020 & rateDataWithType$month >= 2 & rateDataWithType$paperType == 'other','count'])

sarscov2_notretracted <- sarscov2_count - sarscov2_retracted_count
other_notretracted <- other_count - other_retracted_count


retraction_table <- matrix(c(sarscov2_retracted_count, sarscov2_notretracted, other_retracted_count, other_notretracted),
       nrow = 2,
       dimnames = list(WasRetracted = c("Yes", "No"),
                       Focus = c("SARS-CoV-2", "Other")))
fisher.test(retraction_table, alternative = "greater")



data <- read.table('data/retracted_data.tsv',sep='\t',quote='')
colnames(data) <- c('pmid','is_sarscov2_paper', 'is_preprint', 'is_retracted', 'has_retraction_flag','title','published_year','published_month','published_day','revised_year','revised_month','revised_day')

data$is_sarscov2_paper <- data$is_sarscov2_paper == 'True'
data$is_preprint <- data$is_preprint == 'True'
data$is_retracted <- data$is_retracted == 'True'
data$has_retraction_flag <- data$has_retraction_flag == 'True'

data <- data[data$published_year==2020 & data$published_month>=2, ]

not_retracted_records <- data[!data$is_retracted,]
not_retracted_records <- not_retracted_records[order(not_retracted_records$published_year,not_retracted_records$published_month,not_retracted_records$published_day),]
not_retracted_records <- not_retracted_records[!duplicated(not_retracted_records$pmid),]
not_retracted_records <- not_retracted_records[,c('pmid','is_sarscov2_paper', 'is_preprint', 'is_retracted', 'has_retraction_flag','title','published_year','published_month','published_day')]

retracted_records <- data[data$is_retracted,]
retracted_records <- retracted_records[order(retracted_records$revised_year,retracted_records$revised_month,retracted_records$revised_day),]
retracted_records <- retracted_records[!duplicated(retracted_records$pmid),]
retracted_records <- retracted_records[,c('pmid','revised_year','revised_month','revised_day')]
colnames(retracted_records) <- c('pmid','retracted_year','retracted_month','retracted_day')

retractions <- join(not_retracted_records,retracted_records,by=c("pmid"="pmid"))

plyr::count(retractions$is_sarscov2_paper)

retraction_table <- matrix(c(19, 55024, 149, 894183),
                           nrow = 2,
                           dimnames = list(WasRetracted = c("Yes", "No"),
                                           Focus = c("SARS-CoV-2", "Other")))
fisher.test(retraction_table, alternative = "greater")
