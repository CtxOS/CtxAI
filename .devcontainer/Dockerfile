# Base image with Python 3.12 slim
FROM mcr.microsoft.com/devcontainers/python:3.12-bullseye

# Clean apt cache and reduce layers
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git curl wget build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Optional: remove unwanted preinstalled Python packages to save space
RUN pip freeze | xargs pip uninstall -y || true

# Create workspace directory
WORKDIR /workspace

# Set default shell
SHELL ["/bin/bash", "-c"]
