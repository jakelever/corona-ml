
library(ggplot)

biomedAuthors <- data.frame(background=c('No Biomed','Some Biomed'), count=c(1198047,3727473))

ggplot(data=biomedAuthors, aes(x=background, y=count)) +
  geom_bar(stat="identity") + 
  labs(x = "Research Background", y = "Number of Authors") + 
  scale_y_continuous(labels = comma)

authorsOtherPapers <- read.table('data/authorsOtherPapers.csv',sep=',')
colnames(authorsOtherPapers) <- c('Category','Count')

authorsOtherPapers <- authorsOtherPapers[order(authorsOtherPapers$Count,decreasing = T),]
authorsOtherPapers$Category <- factor(as.character(authorsOtherPapers$Category),levels=as.character(authorsOtherPapers$Category))

ggplot(data=authorsOtherPapers, aes(x=Category, y=Count)) +
  geom_bar(stat="identity") + 
  labs(x = "Category", y = "Number of Papers") + 
  theme(axis.text.x=element_text(angle = 65, hjust = 1)) +
  scale_y_continuous(labels = comma)


paperBackgrounds <- data.frame(background=c('>= 1 Authors have some biomed background','Zero authors have biomed background','No author information available'),
                               count=c(51711,3437,8616))


ggplot(data=paperBackgrounds, aes(x=background, y=count)) +
  geom_bar(stat="identity") + 
  labs(x = "Background of Paper's Authors", y = "Number of Papers") + 
  theme(axis.text.x=element_text(angle = 45, hjust = 1)) +
  scale_y_continuous(labels = comma)


nonbiobackgroundTopics <- read.table('data/nonbiobackgroundTopics.csv',sep=',')
colnames(nonbiobackgroundTopics) <- c('topic','count')

ggplot(data=nonbiobackgroundTopics, aes(x=topic, y=count)) +
  geom_bar(stat="identity") + 
  labs(x = "", y = "Number of Papers") + 
  theme(axis.text.x=element_text(angle = 45, hjust = 1)) +
  scale_y_continuous(labels = comma)


allTopics <- read.table('data/allTopics.csv',sep=',')
colnames(allTopics) <- c('topic','count')

ggplot(data=allTopics, aes(x=topic, y=count)) +
  geom_bar(stat="identity") + 
  labs(x = "", y = "Number of Papers") + 
  theme(axis.text.x=element_text(angle = 45, hjust = 1)) +
  scale_y_continuous(labels = comma)

library(lattice)

barchart( count ~ topic, allTopics)
