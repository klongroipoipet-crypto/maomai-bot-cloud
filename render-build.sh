#!/usr/bin/env bash
sed-i 's/\r//g' requirements.txt
pip install -r requirements.txt
