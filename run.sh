if [ -d ".git/" ]; then
	git pull
fi

python3 -B src/
