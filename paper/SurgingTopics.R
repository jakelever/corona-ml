
topicYearDiffs <- read.table('data/yearEntityDiffs_top.tsv',sep='\t',quote='')
colnames(topicYearDiffs) <- c('diff','prev_count','next_count','year','entity_type','entity_id','entity_name')

topicYearDiffs <- topicYearDiffs[order(topicYearDiffs$diff,decreasing=T),]
topicYearDiffs <- topicYearDiffs[topicYearDiffs$entity_type!='Species',]
topicYearDiffs <- topicYearDiffs[topicYearDiffs$entity_id!='-',]

topicYearDiffs$label <- paste(topicYearDiffs$entity_name,' : ', topicYearDiffs$year,'-', topicYearDiffs$year+1, sep='')

selected <- topicYearDiffs[1:10,]

selected$label <- factor(as.character(selected$label),levels=as.character(selected$label))

library(ggplot2)

ggplot(data=selected, aes(x=label, y=diff)) +
  geom_bar(stat="identity") +
  theme(axis.text.x=element_text(angle = 60, hjust = 1)) +
  labs(x = "Entity with Year Change", y = "Year on Year Increase in Papers")

selected2010 <- topicYearDiffs[topicYearDiffs$year==2010,][1:10,]
selected2010$label <- factor(as.character(selected2010$label),levels=as.character(selected2010$label))

ggplot(data=selected2010, aes(x=label, y=diff)) +
  geom_bar(stat="identity") +
  theme(axis.text.x=element_text(angle = 60, hjust = 1)) +
  labs(x = "Entity with Year Change", y = "Year on Year Increase in Papers")

library(data.table)
topicCounts <- fread("data/yearEntityCounts.tsv",sep="\t",quote="")
colnames(topicCounts) <- c('count','year','entity_type','entity_id')
topicCounts$yearStr <- as.character(topicCounts$year)

setorder(topicCounts, year)

meshAnxiety = 'MESH:D001007'
meshDeath = 'MESH:D003643'

anxietyCounts <- topicCounts[topicCounts$entity_id==meshAnxiety & topicCounts$year >= 2010,]
deathCounts <- topicCounts[topicCounts$entity_id==meshDeath & topicCounts$year >= 2010,]

ggplot(data=anxietyCounts, aes(x=yearStr, y=count)) +
  geom_bar(stat="identity") +
  labs(title='Anxiety over the Years', y = "Papers with mention", x = "Year")

ggplot(data=deathCounts, aes(x=yearStr, y=count)) +
  geom_bar(stat="identity") +
  labs(title='Death over the Years', y = "Papers with mention", x = "Year")
