#!/usr/bin/env bash
# Usage: ./ingest.sh <path-to-pdf-or-directory>
# Runs the PDF ingestion pipeline inside the running 'cli' container.

set -e
if [ $# -lt 1 ]; then
  echo "Usage: $0 <path-to-document(s)>"
  exit 1
fi

docker compose -f docker/docker-compose.yml exec cli python backend/ingest_pdf.py --data-dir "$@" 