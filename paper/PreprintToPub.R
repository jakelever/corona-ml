
library(ggplot2)
library(plyr)

papers <- read.table('data/biorxiv_data.tsv')
colnames(papers) <- c('doi','is_sarscov2_paper','is_published','days_til_pub','biorxiv_year','biorxiv_month','biorxiv_day','published_year','published_month','published_date')

papers$is_sarscov2_paper <- papers$is_sarscov2_paper == 'True'
papers$is_published <- papers$is_published == 'True'

papers$label <- 'NA'
papers$label[papers$biorxiv_year==2019] <- '2019'
papers$label[papers$biorxiv_year==2020 & papers$is_sarscov2_paper] <- '2020 - SARS-CoV-2'
papers$label[papers$biorxiv_year==2020 & !papers$is_sarscov2_paper] <- '2020 - Other'

counts <- plyr::count(papers$label)


published <- papers[papers$is_published,]
published_stats <- plyr::count(published$label)

published_with_date <- papers[!is.na(papers$days_til_pub),]
published_with_date_stats <- plyr::count(published_with_date$label)
                         
ggplot(published_with_date, aes(x=label, y=days_til_pub)) + 
  geom_boxplot() +
  labs(x = "Paper Group", y = "Days from Preprint to Publication")

papers_2019 <- papers[papers$biorxiv_year==2019,]
papers_2020_sarscov2 <- papers[papers$biorxiv_year==2020 & papers$is_sarscov2_paper,]
papers_2020_other <- papers[papers$biorxiv_year==2020 & !papers$is_sarscov2_paper,]

papers_2020_sarscov2 <- papers_2020_sarscov2[papers_2020_sarscov2$biorxiv_month <= 6,]
papers_2020_other <- papers_2020_other[papers_2020_other$biorxiv_month <= 6,]

papers_2019_days_til_pub <- papers_2019$days_til_pub[!is.na(papers_2019$days_til_pub)]
papers_2020_sarscov2_days_til_pub <- papers_2020_sarscov2$days_til_pub[!is.na(papers_2020_sarscov2$days_til_pub)]
papers_2020_other_days_til_pub <- papers_2020_other$days_til_pub[!is.na(papers_2020_other$days_til_pub)]

days <- c()
percs_2019 <- c()
percs_2020_sarscov2 <- c()
percs_2020_other <- c()

for (day in 1:100) {
  perc_2019 <- 100*sum(papers_2019_days_til_pub <= day) / nrow(papers_2019)
  perc_2020_sarscov2 <- 100*sum(papers_2020_sarscov2_days_til_pub <= day) / nrow(papers_2020_sarscov2)
  perc_2020_other <- 100*sum(papers_2020_other_days_til_pub <= day) / nrow(papers_2020_other)
  
  days <- c(days,day)
  percs_2019 <- c(percs_2019,perc_2019)
  percs_2020_sarscov2 <- c(percs_2020_sarscov2,perc_2020_sarscov2)
  percs_2020_other <- c(percs_2020_other,perc_2020_other)
}

survival_data <- data.frame(day=days,y2019=percs_2019,y2020_sarscov2=percs_2020_sarscov2,y2020_other=percs_2020_other)



library(tidyr)

survival_long <- gather(survival_data, group, perc, y2019:y2020_other, factor_key=TRUE)

ggplot(survival_long, aes(x=day, y=perc, group=group)) + 
  geom_line(aes(color=group)) +
  labs(x = "Days After Preprint", y = "Papers Published (%)")
