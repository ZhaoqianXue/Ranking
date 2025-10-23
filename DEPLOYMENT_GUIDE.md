# Render Deployment Guide

This guide provides instructions for deploying the Spectral Ranking application to Render. The application consists of two services: a Python FastAPI backend and a Python NiceGUI frontend.

## 1. Project Structure for Deployment

To streamline deployment, we have defined the necessary configuration in `render.yaml`. This file sets up both the backend and frontend services. The backend will be deployed as a Docker container to include the R environment, while the frontend will be deployed as a standard Python web service.

The user has specified that only a subset of files are used. The `Dockerfile.backend` and `render.yaml` are configured to copy and use only the necessary parts of the application.

## 2. Prerequisites

- A Render account.
- Your project code pushed to a GitHub repository.

## 3. Deployment Steps

1.  **Create a new "Blueprint" service on Render.**
    - In your Render dashboard, click "New +" and select "Blueprint".
    - Connect the GitHub repository containing your project.
    - Render will automatically detect the `render.yaml` file in your repository.

2.  **Configure Environment Variables.**
    - After creating the Blueprint, navigate to the "Environment" tab for your `ranking-backend` service.
    - You need to add a secret file or environment variable for `OPENAI_API_KEY`.
    - Click "Add Secret File" or "Add Environment Variable".
    - Set the key to `OPENAI_API_KEY` and paste your OpenAI API key in the value field.

3.  **Deploy.**
    - Click "Create New Blueprint" or "Deploy" to start the deployment process.
    - Render will build and deploy both the backend and frontend services according to the `render.yaml` configuration.
    - You can monitor the deployment logs for both services in the Render dashboard.

## 4. Accessing Your Application

- Once the deployment is complete, Render will provide a public URL for your `ranking-frontend` service (e.g., `https://ranking-frontend.onrender.com`).
- The backend service (`ranking-backend`) will be accessible internally by the frontend service. Its URL is automatically passed to the frontend via the `API_BASE_URL` environment variable.

## 5. Service Configuration Summary (`render.yaml`)

-   **`ranking-backend`**:
    -   **Type**: Docker Web Service.
    -   **Dockerfile**: `Dockerfile.backend` (includes Python, R, and dependencies).
    -   **Health Check**: `/api/health` endpoint.
    -   **Environment**: Requires `OPENAI_API_KEY`.
    -   **Disk**: A persistent disk is attached to store `data_llm` files if needed, although the current configuration copies the necessary data file into the Docker image.

-   **`ranking-frontend`**:
    -   **Type**: Python Web Service.
    -   **Build Command**: `pip install -r frontend_requirements.txt`.
    -   **Start Command**: `python code_app/frontend/main.py`.
    -   **Environment**: `API_BASE_URL` is automatically set to the backend's URL.

This setup ensures a clean, reproducible, and scalable deployment on Render.
