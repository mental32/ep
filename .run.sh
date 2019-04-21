#!/bin/bash

if python -c "import sys; sys.exit(hasattr(sys, \"real_prefix\"))"; then
	python -Bm src
else
	pipenv run python -Bm src
fi
