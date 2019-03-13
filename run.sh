if [ -d ".git/" ]; then
	git pull
fi

python -B src/
