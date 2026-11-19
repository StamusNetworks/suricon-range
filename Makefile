setup:
	pip install --upgrade python/adsim

NOTEBOOKS = $(shell find . -type f -name '*.ipynb' -not -path '*/.*')

clean:
	jupyter nbconvert --clear-output --inplace $(NOTEBOOKS)

NB ?= presentation.ipynb

html:
	jupyter nbconvert --to html --output-dir ./ $(NB)

pdf: html
	weasyprint $(basename $(NB)).html $(basename $(NB)).pdf

.PHONY: setup clean html pdf
