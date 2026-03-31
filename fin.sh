#!/data/data/com.termux/files/usr/bin/bash

SCRIPT="$(dirname "$0")/money_graph.py"

# Check python
if ! command -v python >/dev/null 2>&1; then
  echo "[ERROR] Python not found"
  exit 1
fi

# Check rich
python -c "import rich" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Installing rich library..."
  pip install rich
fi

# If no argument
if [ -z "$1" ]; then
  echo
  echo "Enter path to .txt file:"
  echo
  read -p "File: " F
  python "$SCRIPT" "$F"
else
  python "$SCRIPT" "$1"
fi

echo
read -p "Press Enter to exit..."
