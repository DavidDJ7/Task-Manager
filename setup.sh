#!/bin/bash

# Setup script for Task Manager AI (Linux/macOS)

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete."
echo "To start the app, run:"
echo "  source venv/bin/activate"
