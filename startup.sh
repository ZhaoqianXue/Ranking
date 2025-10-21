#!/bin/bash

# Install minimal R for spectrum ranking (no GUI dependencies)
apt-get update
apt-get install -y r-base r-base-dev libcurl4-openssl-dev libssl-dev libxml2-dev

# Install only required R packages for spectrum ranking
R -e "install.packages(c('readr', 'dplyr', 'jsonlite'), repos='https://cran.r-project.org/', dependencies=TRUE)"

# Create necessary directories
mkdir -p /home/site/wwwroot/jobs
mkdir -p /home/site/wwwroot/agent_uploads
mkdir -p /home/site/wwwroot/temp_ranking_jobs

# Set proper permissions
chmod -R 755 /home/site/wwwroot/jobs
chmod -R 755 /home/site/wwwroot/agent_uploads
chmod -R 755 /home/site/wwwroot/temp_ranking_jobs

# Start the backend API
uvicorn code_app.backend.main:app --host 0.0.0.0 --port $PORT
