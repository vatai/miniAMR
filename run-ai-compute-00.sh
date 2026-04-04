#!/bin/bash

ARGS=(
  --method FugakuEvoTADASHI 
  --n-threads 1 
  --population-size=20 
  --max-gen=50
)

LOGFILE=$(mktemp  -p . "$(basename $(pwd)).$(date -I).XXXXX.log")
python -u app.py "${ARGS[@]}" 2>&1 > "$LOGFILE"

