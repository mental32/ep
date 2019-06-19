#!/usr/bin/make -f

python := python3
pipenv := pipenv

.PHONY: install run

install:
	git pull
	$(pipenv) install

run:
	@sh ./tools/.run.sh
