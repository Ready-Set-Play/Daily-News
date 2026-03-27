#!/bin/bash
# test.sh — Run the daily-brief test suite
# Usage:
#   ./test.sh           Run all tests (cassette tests skipped if not recorded)
#   ./test.sh pipeline  Run only the pipeline smoke tests (fastest, no cassettes)
#   ./test.sh record    Record all VCR cassettes (requires real API keys in .env)

set -e
cd "$(dirname "$0")"

# Load .env if present
if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

case "${1:-all}" in
  pipeline)
    PYTHONPATH=src pytest tests/test_pipeline.py -v
    ;;
  record)
    # Uses prod .env if project .env has empty keys
    if [ -f ~/Scripts/daily-brief/.env ] && ! grep -q "NYT_API_KEY=." .env 2>/dev/null; then
      set -o allexport; source ~/Scripts/daily-brief/.env; set +o allexport
    fi
    PYTHONPATH=src pytest tests/sources/ -v
    ;;
  *)
    PYTHONPATH=src pytest tests/ -v
    ;;
esac
