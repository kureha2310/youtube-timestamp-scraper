#!/bin/bash
echo "========================================"
echo "  ワンクリックWeb更新"
echo "========================================"
echo

python3 update_web.py
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo
    echo "[!] エラーが発生しました"
    exit $exit_code
fi

echo
