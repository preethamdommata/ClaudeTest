#!/bin/bash
# ATF launcher — always uses the correct Python installation
PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$SCRIPT_DIR"
"$PYTHON" runner.py "$@"
