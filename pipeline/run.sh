#!/bin/bash

# Compatible environment activation (Windows vs macOS/Linux)
if [ -d "./venv/Scripts" ]; then
    source ./venv/Scripts/activate
elif [ -d "./store-intelligence/venv/Scripts" ]; then
    source ./store-intelligence/venv/Scripts/activate
elif [ -d "./venv/bin" ]; then
    source ./venv/bin/activate
else
    source ./store-intelligence/venv/bin/activate
fi

# Launch detect coordinator
python pipeline/detect.py "$@"
