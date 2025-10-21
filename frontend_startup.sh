#!/bin/bash

# Create necessary directories
mkdir -p /home/site/wwwroot/jobs
mkdir -p /home/site/wwwroot/agent_uploads
mkdir -p /home/site/wwwroot/temp_ranking_jobs

# Set proper permissions
chmod -R 755 /home/site/wwwroot/jobs
chmod -R 755 /home/site/wwwroot/agent_uploads
chmod -R 755 /home/site/wwwroot/temp_ranking_jobs

# Start the NiceGUI frontend
python code_app/frontend/main.py
