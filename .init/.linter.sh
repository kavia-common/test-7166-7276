#!/bin/bash
cd /home/kavia/workspace/code-generation/test-7166-7276/FlaskBackend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

