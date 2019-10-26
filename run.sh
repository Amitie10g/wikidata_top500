#!/bin/bash

# :: This script is intended for running under Toolforge

# Set environment variables
VENV_PATH=$HOME/venv
SCRIPT_PATH=$HOME/wikidata_top500
TASK_NAME=top500importer

# Install Python3 and libraries at Virtualenv ($HOME/venv), if needed
if [ ! -f "$VENV_PATH/bin/python" ]; then
	virtualenv -p python3 "$HOME/venv"
	source "$HOME/venv/bin/activate"
	pip install --upgrade pip
	pip install beautifulsoup4 redis requests
fi

# Generate Wiki user and password, if needed
if [ ! -f "$HOME/user-config.py" ] && [ ! -f "$HOME/user-password.py" ]; then
	"$VENV_PATH/bin/python" \
	"$SCRIPT_PATH/pywikibot/pwb.py" \
	"$SCRIPT_PATH/pywikibot/generate_user_files.py"
	chmod 600 "$HOME/user-config.py" "$HOME/user-password.py"
fi

if [ -n "$1" ]; then
	MUL=$1
else
	MUL=1
fi

# Get the task status
qstat -j "$TASK_NAME$MUL" > /dev/null
STATUS=$?

# If task is stopped, start
if [ $STATUS == 1 ]; then
	echo "Want to start? Press CONTROL , C to cancel"
	sleep 1
	echo "3"
	sleep 1
	echo "2"
	sleep 1
	echo "1"
	sleep 1
	jstart -N \
		"$TASK_NAME$MUL" \
		"$VENV_PATH/bin/python" \
		"$SCRIPT_PATH/pywikibot/pwb.py" \
		"$SCRIPT_PATH/main.py" \
		--mass \
		"$MUL"

# If task is running, stop
else
	echo "Want to stop? Press CONTROL , C to cancel"
	sleep 1
	echo "3"
	sleep 1
	echo "2"
	sleep 1
	echo "1"
	sleep 1
	jstop "$TASK_NAME$MUL"
fi
