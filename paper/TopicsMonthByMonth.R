
library(ggplot2)

data <- read.table('data/topicsMonthByMonth.tsv',sep='\t')
colnames(data) <- c('year','month','topic','virus','count')

data <- data[data$topic != 'Unknown',]

sarscov2 <- data[data$virus == 'SARS-CoV-2' & data$year == 2020,]

ggplot(data=sarscov2, aes(x=month, y=count, group=topic)) +
  geom_line(aes(color=topic)) + 
  scale_x_continuous(breaks=seq(1,12,1)) + 
  labs(x = "Month of 2020", y = "Number of papers")

ggplot(data=sarscov2, aes(x=month, y=count, fill=topic)) +
  geom_area()

library(dplyr)

sarscov2_proportional <- sarscov2  %>%
  group_by(month, topic) %>%
  summarise(n = sum(count)) %>%
  mutate(percentage = n / sum(n))

ggplot(data=sarscov2_proportional, aes(x=month, y=percentage, fill=topic)) +
  geom_area()


topTopics <- plyr::count(sarscov2,~ topic, ~ count)
chosenTopics <- topTopics$topic[order(topTopics$freq,decreasing=T)][1:5]

ggplot(data=sarscov2_proportional[sarscov2_proportional$topic %in% chosenTopics & sarscov2_proportional$month > 1,], aes(x=month, y=100*percentage, group=topic)) +
  geom_line(aes(color=topic)) + 
  scale_x_continuous(breaks=seq(1,12,1)) + 
  labs(x = "Month of 2020", y = "Percentage of Topic Labels")


ggplot(data=sarscov2[sarscov2$topic %in% chosenTopics,], aes(x=month, y=count, group=topic)) +
  geom_line(aes(color=topic)) + 
  scale_x_continuous(breaks=seq(1,12,1)) + 
  labs(x = "Month of 2020", y = "Counts of Topic Labels")
