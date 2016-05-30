all:
	rm -f karma.db
	python -c "import karmabot; karmabot.init_database()"
