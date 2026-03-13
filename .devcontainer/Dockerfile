# syntax=docker/dockerfile:1
# This Dockerfile is used to build the devcontainer image for GitHub Codespaces
# It includes optimizations for faster startup and better caching

FROM mcr.microsoft.com/devcontainers/python:3.12

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv with caching support
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Create uv cache directories
RUN mkdir -p /usr/local/share/uv-cache /usr/local/share/uv-tool-cache
ENV UV_CACHE_DIR=/usr/local/share/uv-cache
ENV UV_TOOL_CACHE_DIR=/usr/local/share/uv-tool-cache
ENV UV_LINK_MODE=copy
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /workspaces/ctxai

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* ./

# Install dependencies (cached layer)
RUN uv sync --no-dev || true

# Default arguments
ARG USERNAME=vscode
RUN if [ "$USERNAME" != "root" ]; then \
    useradd -m -s /bin/bash $USERNAME && \
    chown -R $USERNAME /workspaces; \
    fi

USER $USERNAME

# Set default VS Code settings
COPY --chown=vscode:vscode .vscode /home/$USERNAME/.vscode

# Post-create command reference (run by Codespaces)
# This is handled by devcontainer.json postCreateCommand
