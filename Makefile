#!/usr/bin/make -f

python := python3
pipenv := pipenv

.PHONY: all run

all:
	git pull
	$(pipenv) install

run:
	@bash .run.sh
