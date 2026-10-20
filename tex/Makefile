# Build skripsi.pdf (butuh XeLaTeX dan biber)
MAIN = skripsi
all: $(MAIN).pdf
$(MAIN).pdf: $(MAIN).tex undipskripsi.sty references.bib front/*.tex bab/*.tex
	xelatex -interaction=nonstopmode $(MAIN)
	biber $(MAIN)
	xelatex -interaction=nonstopmode $(MAIN)
	xelatex -interaction=nonstopmode $(MAIN)
dark: $(MAIN)-dark.pdf
$(MAIN)-dark.pdf: $(MAIN).pdf
	xelatex -interaction=nonstopmode -jobname=$(MAIN)-dark "\\def\\darkmode{}\\input{$(MAIN)}"
	biber $(MAIN)-dark
	xelatex -interaction=nonstopmode -jobname=$(MAIN)-dark "\\def\\darkmode{}\\input{$(MAIN)}"
	xelatex -interaction=nonstopmode -jobname=$(MAIN)-dark "\\def\\darkmode{}\\input{$(MAIN)}"
docx: $(MAIN).pdf
	python3 ../tools/docx/make_docx.py
clean:
	rm -f *.aux *.bbl *.bcf *.blg *.log *.lof *.lot *.out *.run.xml *.toc */*.aux
.PHONY: all clean dark docx
