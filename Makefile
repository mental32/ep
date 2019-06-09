#!/usr/bin/make -f

python := python3
pipenv := pipenv

.PHONY: install

install:
	git pull
	$(pipenv) install
