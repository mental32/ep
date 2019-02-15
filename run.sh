if [ -d ".git/" ]; then
	git pull
fi

python3.6 -B src/
