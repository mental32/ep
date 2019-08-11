#!/bin/bash

if python -c "import sys; sys.exit(not hasattr(sys, \"real_prefix\"))"; then
    echo "info: venv is active."
    python -Bm src
else
    echo "info: venv not activated using \`pipenv\`"
    pipenv run python -Bm src
fi
