#!/bin/bash

pip3 install --user -r requirements.txt

wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install
rm -f aws-sam-cli-linux-x86_64.zip
rm -rf sam-installation/
sam --version
