#!/bin/bash
# Quick activation script for onze-dev-pipeline virtual environment
#
# Usage:
#   source activate.sh
#   . activate.sh

# Activate the virtual environment
source venv/bin/activate

echo "✅ Virtual environment activated!"
echo ""
echo "📝 Quick commands:"
echo "  make dev-pipeline-help        # Show pipeline commands help"
echo "  make dev-pipeline STORY=HUB-  # Start a new pipeline"
echo "  make dev-pipeline-resume STORY=HUB-  # Resume pipeline"
echo "  make dev-pipeline-status      # Check pipeline status"
echo ""
