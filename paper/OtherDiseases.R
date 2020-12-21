
data <- read.table('data/otherDiseases.txt',sep='\t')
colnames(data) <- c('count','year','month','entity_id')


mesh_mapping <- read.table('data/mesh_mapping.tsv',sep='\t',quote='')
colnames(mesh_mapping) <- c('entity_id','entity_name')

data$date <- as.Date(paste(data$year,data$month,'01',sep='-'))

data <- data[order(data$year,data$month),]
data <- data[data$year >= 2010,]
data <- data[!(data$year==2020 & data$month==9),]

data <- left_join(data,mesh_mapping,by=c("entity_id"="entity_id"))

cystic_fibrosis <- 'MESH:D003550'
breast_cancer <- 'MESH:D001943'

selected <- data[data$entity_id == 'MESH:C562470',]
ggplot(data=selected, aes(x=date, y=count)) +
  geom_line() + 
  scale_x_date(labels = date_format("%m-%Y"), date_breaks="1 year") + 
  labs(title=paste("Papers that mention",selected$entity_name[1]), x = "Date", y = "Number of Articles Per Month") +
  theme(axis.text.x=element_text(angle = 60, hjust = 1))


checkTrends <- function(entity_id) {
  selected <- data[data$entity_id == entity_id,]
  
  before2020 <- selected[selected$year < 2020, ]
  
  model <- lm(count ~ date, data = before2020)
  
  new_data <- data.frame(date=as.Date(paste('2020-',3:8,'-01',sep='')))
  new_data$count <- predict(model, new_data)
  
  compared_bit <- selected[selected$date %in% new_data$date,]
  
  predicted_count_for_period <- sum(new_data$count)
  actual_count_for_period <- sum(compared_bit$count)
  
  return (100*(actual_count_for_period - predicted_count_for_period) / predicted_count_for_period)
}

entity_counts <- plyr::count(data, ~entity_id, ~ count)
entity_counts <- entity_counts[order(entity_counts$freq,decreasing=T),]
entity_counts <- entity_counts[entity_counts$freq > 1000, ]

checkTrends('MESH:D009369')

entity_counts$perc_diff <- sapply(entity_counts$entity_id,checkTrends)

entity_counts <- entity_counts[order(entity_counts$perc_diff),]

entity_counts <- left_join(entity_counts,mesh_mapping,by=c("entity_id"="entity_id"))

