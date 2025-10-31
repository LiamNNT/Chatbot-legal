#!/bin/bash
# Script để test backend với debug logging

echo "=================================================="
echo "Test Chatbot-UIT Backend with Debug Logging"
echo "=================================================="
echo ""

# Check if conda environment is activated
if [[ "$CONDA_DEFAULT_ENV" != "chatbot-UIT" ]]; then
    echo "❌ Conda environment 'chatbot-UIT' is not activated!"
    echo "Please run: conda activate chatbot-UIT"
    exit 1
fi

echo "✓ Conda environment: $CONDA_DEFAULT_ENV"
echo ""

# Start backend with debug
echo "Starting backend with debug logging..."
echo "Press Ctrl+C to stop all services"
echo ""

python start_backend.py --debug
