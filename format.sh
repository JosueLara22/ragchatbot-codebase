#!/bin/bash
# Format all Python files using black

echo "Running black formatter..."
uv run black .

echo ""
echo "Formatting complete!"
