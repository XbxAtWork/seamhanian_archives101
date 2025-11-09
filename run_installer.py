#!/usr/bin/env python3
"""
Cross-platform launcher for the Seamhanian Information Program (SIP)
Automatically sets up virtual environment and runs the app.
"""

import os
import sys
import subprocess
import venv

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_PATH = os.path.join(PROJECT_ROOT, ".venv")
PYTHON_EXE = sys.executable  # Current Python

# Step 1: Create virtual environment if it doesn't exist
if not os.path.exists(VENV_PATH):
    print("Creating virtual environment...")
    venv.create(VENV_PATH, with_pip=True)

# Step 2: Determine Python executable inside virtualenv
if os.name == "nt":
    venv_python = os.path.join(VENV_PATH, "Scripts", "python.exe")
else:
    venv_python = os.path.join(VENV_PATH, "bin", "python")

# Step 3: Install requirements if not installed
try:
    import dotenv
except ModuleNotFoundError:
    print("Installing dependencies...")
    subprocess.check_call([venv_python, "-m", "pip", "install", "-r", "requirements.txt"])

# Step 4: Run the main SIP app
subprocess.check_call([venv_python, os.path.join(PROJECT_ROOT, "z.py")])