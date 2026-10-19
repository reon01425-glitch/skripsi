# Build skripsi.pdf (butuh XeLaTeX dan biber)
MAIN = skripsi
all: $(MAIN).pdf
$(MAIN).pdf: $(MAIN).tex undipskripsi.sty references.bib front/*.tex bab/*.tex
	xelatex -interaction=nonstopmode $(MAIN)
	biber $(MAIN)
	xelatex -interaction=nonstopmode $(MAIN)
	xelatex -interaction=nonstopmode $(MAIN)
clean:
	rm -f *.aux *.bbl *.bcf *.blg *.log *.lof *.lot *.out *.run.xml *.toc */*.aux
.PHONY: all clean
