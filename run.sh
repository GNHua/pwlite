#! /bin/bash

ROOT="$( cd "$(dirname "$0")" ; pwd -P )"
echo $ROOT
source $ROOT/env/bin/activate
python $ROOT/run.py
