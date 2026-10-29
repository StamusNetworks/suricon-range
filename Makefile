setup:
	pip install --upgrade python/adsim

NOTEBOOKS = $(shell find ./ -type f -name *.ipynb)

clean:
	jupyter nbconvert --clear-output --inplace $(NOTEBOOKS)
