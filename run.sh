if [ -d ".git/" ]; then
	git pull
fi

python -Bm src
