#!/bin/bash
# Check code formatting without making changes

echo "Checking code formatting with black..."
uv run black --check --diff .

if [ $? -eq 0 ]; then
    echo ""
    echo "All files are properly formatted!"
    exit 0
else
    echo ""
    echo "Some files need formatting. Run ./format.sh to fix."
    exit 1
fi
