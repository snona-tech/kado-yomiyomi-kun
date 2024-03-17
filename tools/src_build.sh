#!/bin/bash
rm -rf ./dist
pip install -r ./requirements.txt --target ./dist
cp ./src/*.py ./dist
rm -rf ./dist/__pycache__ ./dist/README.md