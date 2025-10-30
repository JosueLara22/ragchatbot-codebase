#!/bin/bash
# Run all code quality checks

set -e

echo "======================================"
echo "Running Code Quality Checks"
echo "======================================"
echo ""

echo "1. Checking code formatting..."
echo "------------------------------"
uv run black --check --diff .

echo ""
echo "======================================"
echo "All quality checks passed!"
echo "======================================"
