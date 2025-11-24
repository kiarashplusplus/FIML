#!/bin/bash
# Serve MkDocs documentation locally
# Usage: ./serve_docs.sh

set -e

echo "🔨 Building documentation..."
mkdocs build

echo ""
echo "🚀 Starting documentation server..."
echo "📚 Access documentation at: http://127.0.0.1:8000"
echo "Press Ctrl+C to stop"
echo ""

mkdocs serve
