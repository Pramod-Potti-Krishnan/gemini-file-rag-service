FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Railway assigns PORT dynamically)
EXPOSE ${PORT:-8080}

# Run command - Railway provides PORT env var
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
