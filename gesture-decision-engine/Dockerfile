FROM python:3.11-slim

# Install Node 20 via NodeSource
RUN apt-get update && apt-get install -y curl ca-certificates --no-install-recommends \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs --no-install-recommends \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend deps
COPY frontend/package.json frontend/package.json
RUN cd frontend && npm install --include=dev

# Copy all source
COPY . .

# Build frontend bundle
RUN cd frontend && npm run build

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
