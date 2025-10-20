#!/bin/bash

# Install system dependencies for NiceGUI frontend
apt-get update
apt-get install -y python3-pip

# Create necessary directories
mkdir -p /home/site/wwwroot/jobs
mkdir -p /home/site/wwwroot/agent_uploads

# Set proper permissions
chmod -R 755 /home/site/wwwroot/jobs
chmod -R 755 /home/site/wwwroot/agent_uploads

# Start the NiceGUI frontend
python code_app/frontend/main.py
