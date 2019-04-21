#!/bin/bash

python := python3
pipenv := pipenv

all:
	git pull
	$(pipenv) install

run:
	@bash .run.sh
