FROM mcr.microsoft.com/devcontainers/python:1-3.12

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set workdir and copy project files for install
WORKDIR /workspace

# Use non-root for container operations
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Ensure Python tools
RUN python -m pip install --upgrade pip setuptools wheel

# Ensure uv available (for this repo's script)
RUN python -m pip install uv

# Optional: install default packages from requirements
COPY ./requirements.txt /workspace/requirements.txt
RUN python -m pip install -r /workspace/requirements.txt
