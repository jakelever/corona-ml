#py$category_df$category <- factor(py$category_df$category, levels=py$category_df$category[order(py$category_df$count,decreasing=T)])

ggplot(data=py$topics_by_month_df, aes(x=month, y=perc_in_month, group=category)) +
  geom_line(aes(color=category),size=2) +
  xlab("Month of 2020") + ylab("% of SARS-CoV-2 papers") +
  scale_x_continuous(breaks=1:12) + 
  theme_minimal() + 
  theme(panel.grid.minor = element_blank()) +
  scale_colour_brewer(palette = "Spectral")