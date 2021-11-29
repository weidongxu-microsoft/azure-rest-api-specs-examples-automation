#!/bin/sh

# sudo apt -y install golang-go
sudo apt -y install golang-golang-x-tools

python3 go/main.py "$@"
