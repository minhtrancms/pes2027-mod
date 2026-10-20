#!/usr/bin/env bash
# Quick local test runner for PHP server
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

PORT=8080
echo "=========================================================="
echo "   eFootball 2027 PHP Server (Local Test)"
echo "   Open: http://localhost:$PORT"
echo "=========================================================="
php -S 0.0.0.0:$PORT
