#!/usr/bin/env python3
import subprocess
import os

os.chdir("PATH TO YOUR APP DIRECTORY")  # Change to the directory where your app.py is located
subprocess.run(["PATH TO YOUR VENV/bin/streamlit", "run", "app.py"])
