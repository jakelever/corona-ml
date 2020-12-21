
library(ggplot2)
library(zoo)
library(plyr)
library(dplyr)
library(scales)

rateDataWithType = read.table('data/publicationRateWithMore.tsv')
colnames(rateDataWithType) <- c('count','year','month','paperType')

rateData <- aggregate(rateDataWithType$count,list(year=rateDataWithType$year,month=rateDataWithType$month),sum)
colnames(rateData) <- c('year','month','count')

rateData <- rateData[order(rateData$year,rateData$month),]

rateData <- rateData[rateData$year >= 2000,]

rateData <- rateData[!(rateData$year == 2020 & rateData$month >= 9),]

rateData$yearMonth <- rateData$year + (rateData$month-1) / 12

rateData$yearMonthStr <- paste(rateData$year, rateData$month)


ggplot(data=rateData, aes(x=yearMonthStr, y=count)) +
  geom_bar(stat="identity") 

#for (year in 2000:2020) {
#  for (month in 1:12) {
#    print(year)
#  }
#}

#rateData2 <- rateData %>% dplyr::mutate(rolling_count = zoo::rollmean(count, k = 3, fill = NA))

#rollingAverage <- function(year,month) {
#  
#}

ggplot(data=rateData, aes(x=yearMonth, y=count)) +
  geom_line() + geom_smooth(method = "lm") + 
  theme(panel.grid.major = element_blank(), 
        panel.grid.minor = element_blank(),
        panel.background = element_blank(), 
        axis.line = element_line(colour = "black")) + 
  labs(x = "Date", y = "Articles per month")


#rateData3 <- rateData[order(rateData$count,decreasing=T),]

rateDataWithType$yearMonth <- rateDataWithType$year + (rateDataWithType$month-1) / 12
rateDataWithType$yearMonthStr <- paste(rateDataWithType$year, rateDataWithType$month)

rateDataWithType <- rateDataWithType[rateDataWithType$year >= 2000,]
rateDataWithType <- rateDataWithType[!(rateDataWithType$year == 2020 & rateDataWithType$month >= 9),]

ggplot(data=rateDataWithType, aes(x=yearMonth, y=count, fill=paperType)) +
  geom_bar(position="stack", stat="identity") + 
  theme(panel.grid.major = element_blank(), 
        panel.grid.minor = element_blank(),
        panel.background = element_blank(), 
        axis.line = element_line(colour = "black")) + 
  labs(x = "Date", y = "Articles per month") + 
  scale_y_continuous(labels = comma)

justPreprints <- rateDataWithType[rateDataWithType$paperType %in% c('preprint','corona_preprint'),]

ggplot(data=justPreprints, aes(x=month, y=count, group=paperType)) +
  geom_line(aes(color=paperType)) + 
  labs(x = "Month of 2020", y = "Articles per month")
