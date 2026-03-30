#!/bin/bash
# ATF launcher — run from ClaudeTest root folder
# Usage: ./run.sh --url https://www.saucedemo.com
PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ATF_DIR="$SCRIPT_DIR/atf"

cd "$ATF_DIR"
"$PYTHON" runner.py "$@"
