#! /bin/bash

ROOT="$( cd "$(dirname "$0")" ; pwd -P )"
source $ROOT/env/bin/activate
python $ROOT/run.py
