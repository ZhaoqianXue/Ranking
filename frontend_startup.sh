#!/bin/bash

# Install system dependencies for NiceGUI frontend and R
apt-get update
apt-get install -y python3-pip r-base r-base-dev libcurl4-openssl-dev libssl-dev libxml2-dev libgomp1

# Install minimal R packages required by ranking scripts
R -e "install.packages(c('MASS', 'Matrix', 'stats4'), repos='https://cran.rstudio.com/', dependencies=TRUE)"

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
