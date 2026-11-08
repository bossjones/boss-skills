# Python + VirtualEnv Justfile Example
set shell := ["bash", "-uc"]

# Setup virtual environment and install requirements
setup:
  python3 -m venv venv
  ./venv/bin/pip install -r requirements.txt

# Run the app
run:
  ./venv/bin/python main.py

# Clean up temporary files
clean:
  rm -rf venv
  find . -type d -name "__pycache__" -exec rm -rf {} +

# Run a python script directly within a recipe
hello:
  #!/usr/bin/env python3
  import os
  print(f"Hello from {os.getcwd()}")
