
library(ggplot2)
library(scales)

data <- read.table('data/trending_dates.tsv',sep='\t',quote='')
colnames(data) <- c('doi','title','date_as_real','year','month','day','count')

data$date <- as.Date(paste(data$year,data$month,data$day,sep='-'))
data <- data[data$year>=2020,]

titles <- unique(as.character(data$title))

#title <- 'Chloroquine is a potent inhibitor of SARS coronavirus infection and spread.'
title <- 'Hydroxychloroquine and azithromycin as a treatment of COVID-19: results of an open-label non-randomized clinical trial.'
selected_paper_data <- data[data$title==title,]

ggplot(data=selected_paper_data, aes(x=date, y=count)) +
  geom_line() + 
  scale_x_date(labels = date_format("%m-%Y"), date_breaks="1 month") + 
  labs(x = "Date", y = "Number of Tweets (per day)") +
  geom_vline(xintercept = as.Date("2020-03-21"), color="red", size=1)+
  geom_vline(xintercept = as.Date("2020-05-18"), color="green", size=1)+
  geom_vline(xintercept = as.Date("2020-07-06"), color="blue", size=1)

#as.Date('2019-02-01')
