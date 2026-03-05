#!/bin/bash
# Docker build and run script

set -e

ACTION=${1:-build}
BRANCH=${2:-latest}
NAME=${3:-ctxai}

case "$ACTION" in
    build)
        echo "Building Docker image..."
        docker build -f docker/run/Dockerfile \
            --build-arg BRANCH="$BRANCH" \
            -t ctxai:"$BRANCH" .
        ;;
    run)
        echo "Running Docker container..."
        docker run -d \
            --name "$NAME" \
            -p 50001:80 \
            -v "$(pwd)/usr:/ctx/usr" \
            -e TZ=UTC \
            ctxai:"$BRANCH"
        ;;
    stop)
        echo "Stopping Docker container..."
        docker stop "$NAME" || true
        docker rm "$NAME" || true
        ;;
    logs)
        docker logs -f "$NAME"
        ;;
    shell)
        docker exec -it "$NAME" bash
        ;;
    *)
        echo "Usage: $0 [build|run|stop|logs|shell] [branch] [name]"
        exit 1
        ;;
esac
