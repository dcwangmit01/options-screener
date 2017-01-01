

venv:
	virtualenv -p python3 .venv
	sleep 1
	source .venv/bin/activate

install:
	pip install -r requirements.txt

clean:
	rm -f *.csv *.sqlite

mrclean: clean
	rm -rf .venv
