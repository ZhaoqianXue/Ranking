#!/bin/bash

# Set headless environment for NiceGUI (Azure App Service has no display)
export DISPLAY=:99
export QT_QPA_PLATFORM=offscreen

# Start the NiceGUI frontend
python code_app/frontend/main.py
