#!/bin/bash
set -e

echo "Building frontend..."
cd frontend && npm run build && cd ..

echo "Starting server..."
uvicorn app.main:app --reload --port 8000 --log-level info
