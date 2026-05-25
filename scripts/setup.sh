#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
INSTALL_RAG=0

for arg in "$@"; do
  case "$arg" in
    --rag)
      INSTALL_RAG=1
      ;;
    -h|--help)
      echo "Usage: $0 [--rag]"
      echo
      echo "Default installs only PDF extraction/chunking requirements."
      echo "--rag also installs Chroma, sentence-transformers, and CPU Torch."
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "ERROR: Python 3 was not found on PATH." >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "Virtual environment already exists: $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r "$ROOT_DIR/requirements.txt"

if [ "$INSTALL_RAG" -eq 1 ]; then
  python -m pip install -r "$ROOT_DIR/requirements-rag.txt"
fi

echo
echo "Setup complete."
echo "Activate with:"
echo "  source .venv/bin/activate"
if [ "$INSTALL_RAG" -eq 0 ]; then
  echo
  echo "RAG dependencies were not installed."
  echo "Install them later with:"
  echo "  ./scripts/setup.sh --rag"
fi
echo
echo "Example:"
echo "  python scripts/extract_pages.py docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf --max-pages 20"
