#!/bin/sh

# sudo apt -y install golang-go

export PATH=$PATH:$GOPATH/bin

python3 go/main.py "$@"
