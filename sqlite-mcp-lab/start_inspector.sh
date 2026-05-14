#!/usr/bin/env bash
set -euo pipefail

echo "Starting MCP Inspector for SQLite Lab..."
echo "Server command: python implementation/mcp_server.py"
echo

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: Node.js is not installed or not found in PATH."
  echo "Install Node.js first, then rerun this script."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm is not installed or not found in PATH."
  echo "Install npm first, then rerun this script."
  exit 1
fi

npx -y @modelcontextprotocol/inspector python implementation/mcp_server.py