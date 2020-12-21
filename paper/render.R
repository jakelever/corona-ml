library(bookdown)
library(tinytex)

if (file.exists('_main.Rmd'))
  file.remove('_main.Rmd')

#bookdown::render_book("paper.Rmd", "bookdown::pdf_book", clean = F, encoding = "UTF-8", config_file = "_bookdown.yml")
#bookdown::render_book("paper.Rmd", "bookdown::html_document2", clean=T)

bookdown::render_book("paper.Rmd", "bookdown::word_document2") #, clean=T)

#bookdown::render_book("paper.Rmd", "bookdown::pdf_book")

#tinytex::pdflatex('main.tex')
