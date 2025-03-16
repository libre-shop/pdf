TEX = pandoc
FLAGS = --pdf-engine=xelatex

# Use the values of src, template, and output passed as arguments
$(output) : $(src)
	$(TEX) $(src) -o $@ --template=$(template) $(FLAGS)

.PHONY: clean
clean :
	rm -f /app/data/output/*.pdf

.PHONY: cleanall
cleanall : clean
	rm -rf /app/data/output/*

